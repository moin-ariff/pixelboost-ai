# upscaler.py
import os
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer
import cv2

MODEL_URLS = {
    '2x'    : 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
    '4x'    : 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth',
    '4x_net': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth',
}

_models = {}

def load_model(scale_key: str):
    """Load and initialize a Real-ESRGAN model by key."""
    scale_int = 2 if scale_key == '2x' else 4

    model = RRDBNet(
        num_in_ch=3,
        num_out_ch=3,
        num_feat=64,
        num_block=23,
        num_grow_ch=32,
        scale=scale_int
    )

    upsampler = RealESRGANer(
        scale=scale_int,
        model_path=MODEL_URLS[scale_key],
        model=model,
        tile=400,
        tile_pad=10,
        pre_pad=0,
        half=False
    )
    return upsampler

def get_model(scale_key: str):
    """Return cached model or load it for the first time."""
    if scale_key not in _models:
        print(f'[INFO] Loading {scale_key} model...')
        _models[scale_key] = load_model(scale_key)
        print(f'[INFO] {scale_key} model ready!')
    return _models[scale_key]

def enhance_output(img_np_bgr):
    """
    Gentle post-processing for natural sharp output.
    Applies unsharp mask, contrast, sharpness,
    color boost and noise reduction.
    """
    img_pil = Image.fromarray(img_np_bgr[:, :, ::-1])

    # Subtle unsharp mask for edge sharpness
    img_pil = img_pil.filter(ImageFilter.UnsharpMask(
        radius=0.6,
        percent=60,
        threshold=2
    ))

    # Slight contrast boost
    img_pil = ImageEnhance.Contrast(img_pil).enhance(1.05)

    # Slight sharpness boost
    img_pil = ImageEnhance.Sharpness(img_pil).enhance(1.08)

    # Keep colors natural
    img_pil = ImageEnhance.Color(img_pil).enhance(1.03)

    # Noise reduction
    img_cv = np.array(img_pil)[:, :, ::-1]
    img_cv = cv2.fastNlMeansDenoisingColored(
        img_cv, None,
        h=1.5,
        hColor=1.5,
        templateWindowSize=7,
        searchWindowSize=21
    )
    return img_cv

def run_upscale(img_np, model_key, out_scale):
    """Run upscaling using the specified model."""
    upsampler = get_model(model_key)
    output, _ = upsampler.enhance(img_np, outscale=out_scale)
    return output

def upscale_image(input_path: str, output_path: str, scale: str = '4x') -> str:
    """
    Main upscaling function.
    Supports 2x, 4x, 8x and 16x scales.
    Uses multi-pass processing for 8x and 16x.
    """
    if scale not in ('2x', '4x', '8x', '16x'):
        raise ValueError('Scale must be 2x, 4x, 8x or 16x')

    img    = Image.open(input_path).convert('RGB')
    img_np = np.array(img)[:, :, ::-1]  # RGB to BGR

    print(f'[INFO] Starting {scale} upscaling — original size: {img.size}')

    if scale == '2x':
        output = run_upscale(img_np, '2x', 2)

    elif scale == '4x':
        # Use RealESRNet for best quality
        print('[INFO] Using RealESRNet model for crispy sharp result...')
        output = run_upscale(img_np, '4x_net', 4)

    elif scale == '8x':
        # Pass 1: 4x upscale
        print('[INFO] 8x — Pass 1/2 (4x RealESRNet)...')
        pass1 = run_upscale(img_np, '4x_net', 4)
        # Pass 2: 2x upscale
        print('[INFO] 8x — Pass 2/2 (2x)...')
        output = run_upscale(pass1, '2x', 2)

    elif scale == '16x':
        # Pass 1: 4x upscale
        print('[INFO] 16x — Pass 1/2 (4x RealESRNet)...')
        pass1 = run_upscale(img_np, '4x_net', 4)
        # Pass 2: 4x upscale again
        print('[INFO] 16x — Pass 2/2 (4x RealESRNet)...')
        output = run_upscale(pass1, '4x_net', 4)

    # Apply post-processing
    print('[INFO] Applying post-processing...')
    output = enhance_output(output)

    # Save final output
    output_img = Image.fromarray(output[:, :, ::-1])  # BGR to RGB
    output_img.save(output_path, format='JPEG', quality=97, optimize=True)

    print(f'[INFO] Done! Output size: {output_img.size}')
    return output_path