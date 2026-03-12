# app.py
import os
import uuid
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from upscaler import upscale_image

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ── Page Routes ────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/developer')
def developer():
    return render_template('developer.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# ── Upscale API ────────────────────────────────────────────
@app.route('/upscale', methods=['POST'])
def upscale():
    # Validate image field
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image found in request'}), 400

    file  = request.files['image']
    scale = request.form.get('scale', '4x')

    # Validate file
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'File type not allowed. Use JPG, PNG, WebP or BMP'}), 400

    if scale not in ('2x', '4x', '8x', '16x'):
        return jsonify({'success': False, 'message': 'Scale must be 2x, 4x, 8x or 16x'}), 400

    # Save file locally for processing
    ext         = file.filename.rsplit('.', 1)[1].lower()
    unique_id   = str(uuid.uuid4())
    input_path  = os.path.join(UPLOAD_FOLDER, f'{unique_id}.{ext}')
    output_path = os.path.join(OUTPUT_FOLDER, f'{unique_id}_{scale}_upscaled.jpg')
    file.save(input_path)

    # Upload original to Cloudinary
    try:
        input_upload = cloudinary.uploader.upload(
            input_path,
            folder='ai-upscaler/originals',
            public_id=f'original_{unique_id}',
            resource_type='image'
        )
        print(f'[INFO] Original uploaded to Cloudinary: {input_upload["secure_url"]}')
    except Exception as e:
        print(f'[WARNING] Cloudinary original upload failed: {e}')

    # Run AI processing
    try:
        upscale_image(input_path, output_path, scale=scale)
    except Exception as e:
        return jsonify({'success': False, 'message': f'AI processing error: {str(e)}'}), 500

# Upload output to Cloudinary (only 2x and 4x — small files)
    if scale in ('2x', '4x'):
        try:
            output_upload = cloudinary.uploader.upload(
                output_path,
                folder='ai-upscaler/upscaled',
                public_id=f'upscaled_{unique_id}_{scale}',
                resource_type='image'
            )
            cloud_url = output_upload['secure_url']
            print(f'[INFO] Output uploaded to Cloudinary: {cloud_url}')

            # Delete local files
            os.remove(input_path)
            os.remove(output_path)

        except Exception as e:
            print(f'[WARNING] Cloudinary upload failed: {e}')
            cloud_url = f'/download/{unique_id}/{scale}'
    else:
        # 8x and 16x — serve directly for perfect quality
        print(f'[INFO] {scale} image — serving directly (max quality)')
        os.remove(input_path)  # Delete input only, keep output
        cloud_url = f'/download/{unique_id}/{scale}'

    return jsonify({
        'success'   : True,
        'output_id' : unique_id,
        'scale'     : scale,
        'image_url' : cloud_url,
        'message'   : f'Image successfully upscaled at {scale}'
    })

# ── Download Fallback ──────────────────────────────────────
@app.route('/download/<output_id>/<scale>', methods=['GET'])
def download(output_id, scale):
    path = os.path.join(OUTPUT_FOLDER, f'{output_id}_{scale}_upscaled.jpg')
    if not os.path.exists(path):
        return jsonify({'error': 'File not found'}), 404
    
    # Send file then delete it
    response = send_file(path, mimetype='image/jpeg', as_attachment=False)
    
    @response.call_on_close
    def delete_after_send():
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f'[INFO] Local file deleted after download: {path}')
        except Exception as e:
            print(f'[WARNING] Could not delete file: {e}')
    
    return response

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=7860)
