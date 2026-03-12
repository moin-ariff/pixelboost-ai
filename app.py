# app.py
import os
import uuid
import threading
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from upscaler import upscale_image

load_dotenv()

app = Flask(__name__)
CORS(app)

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

# Job status store
jobs = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(job_id, input_path, output_path, scale):
    """Background thread mein image process karo"""
    try:
        jobs[job_id]['status'] = 'processing'

        # Upload original to Cloudinary
        try:
            input_upload = cloudinary.uploader.upload(
                input_path,
                folder='ai-upscaler/originals',
                public_id=f'original_{job_id}',
                resource_type='image'
            )
            print(f'[INFO] Original uploaded to Cloudinary: {input_upload["secure_url"]}')
        except Exception as e:
            print(f'[WARNING] Cloudinary original upload failed: {e}')

        # Run AI processing
        upscale_image(input_path, output_path, scale=scale)

        # Upload output to Cloudinary (only 2x and 4x)
        if scale in ('2x', '4x'):
            try:
                output_upload = cloudinary.uploader.upload(
                    output_path,
                    folder='ai-upscaler/upscaled',
                    public_id=f'upscaled_{job_id}_{scale}',
                    resource_type='image'
                )
                cloud_url = output_upload['secure_url']
                print(f'[INFO] Output uploaded to Cloudinary: {cloud_url}')
                os.remove(input_path)
                os.remove(output_path)
                jobs[job_id]['image_url'] = cloud_url
            except Exception as e:
                print(f'[WARNING] Cloudinary output upload failed: {e}')
                os.remove(input_path)
                jobs[job_id]['image_url'] = f'/download/{job_id}/{scale}'
        else:
            print(f'[INFO] {scale} — serving directly')
            os.remove(input_path)
            jobs[job_id]['image_url'] = f'/download/{job_id}/{scale}'

        jobs[job_id]['status'] = 'done'

    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
        print(f'[ERROR] Job {job_id} failed: {e}')

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
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image found in request'}), 400

    file  = request.files['image']
    scale = request.form.get('scale', '4x')

    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'File type not allowed'}), 400

    if scale not in ('2x', '4x', '8x', '16x'):
        return jsonify({'success': False, 'message': 'Scale must be 2x, 4x, 8x or 16x'}), 400

    ext         = file.filename.rsplit('.', 1)[1].lower()
    job_id      = str(uuid.uuid4())
    input_path  = os.path.join(UPLOAD_FOLDER, f'{job_id}.{ext}')
    output_path = os.path.join(OUTPUT_FOLDER, f'{job_id}_{scale}_upscaled.jpg')
    file.save(input_path)

    # Job register karo
    jobs[job_id] = {
        'status'   : 'queued',
        'scale'    : scale,
        'image_url': None,
        'error'    : None
    }

    # Background thread mein process karo
    thread = threading.Thread(
        target=process_image,
        args=(job_id, input_path, output_path, scale)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'success': True,
        'job_id' : job_id,
        'scale'  : scale,
        'message': 'Processing started'
    })

# ── Status Check ───────────────────────────────────────────
@app.route('/status/<job_id>', methods=['GET'])
def status(job_id):
    if job_id not in jobs:
        return jsonify({'status': 'not_found'}), 404

    job = jobs[job_id]

    if job['status'] == 'done':
        return jsonify({
            'status'   : 'done',
            'image_url': job['image_url'],
            'scale'    : job['scale']
        })
    elif job['status'] == 'error':
        return jsonify({
            'status': 'error',
            'error' : job['error']
        })
    else:
        return jsonify({'status': job['status']})

# ── Download ───────────────────────────────────────────────
@app.route('/download/<job_id>/<scale>', methods=['GET'])
def download(job_id, scale):
    path = os.path.join(OUTPUT_FOLDER, f'{job_id}_{scale}_upscaled.jpg')
    if not os.path.exists(path):
        return jsonify({'error': 'File not found'}), 404

    response = send_file(path, mimetype='image/jpeg', as_attachment=False)

    @response.call_on_close
    def delete_after_send():
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f'[INFO] Local file deleted: {path}')
        except Exception as e:
            print(f'[WARNING] Could not delete file: {e}')

    return response

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=7860, threaded=True)
    