import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import requests
import time
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Import the module to access dynamically overridden paths
import Models.config as models_config
from Models.Image.utils import ensure_save_directory

logger = logging.getLogger(__name__)

# Configuration
MAX_RETRIES = 3
INITIAL_DELAY = 2
TIMEOUT = 60
POLL_INTERVAL = 2  # seconds between status checks
MAX_POLL_ATTEMPTS = 30  # Max 60 seconds waiting

# Prodia API endpoints
PRODIA_BASE_URL = "https://api.prodia.com/v1"
PRODIA_GENERATE_URL = f"{PRODIA_BASE_URL}/sdxl/generate"
PRODIA_JOB_URL = f"{PRODIA_BASE_URL}/job"

# Available SDXL models on Prodia (free, no API key needed for basic usage)
SDXL_MODELS = [
    "sd_xl_base_1.0.safetensors [be9edd61]",
    "dreamshaperXL_v21TurboDPMSDE.safetensors [4496b36d]",
    "juggernautXL_v45.safetensors [e75f5471]",
]


class ImageGenerator:
    def __init__(self):
        self.prompt_generator = None
        self.failed_images = []
        self.successful_images = []

    def set_prompt_generator(self, prompt_generator):
        self.prompt_generator = prompt_generator

    def generate_image_prompt(self, text):
        if self.prompt_generator:
            text = self.prompt_generator.generate_prompt(text)
        
        # Optimize prompt for SDXL
        text = text.split(".")[0]  # take first sentence
        text = text[:300]  # SDXL can handle longer prompts
        return text.strip()

    def _create_placeholder_image(self, prompt, img_number, filename):
        """Create a placeholder image when API fails"""
        try:
            width, height = 720, 1280
            img = Image.new('RGB', (width, height), color=(30, 30, 40))
            draw = ImageDraw.Draw(img)
            
            # Add gradient
            for y in range(height):
                r = int(30 + (y / height) * 20)
                g = int(30 + (y / height) * 15)
                b = int(40 + (y / height) * 25)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            draw = ImageDraw.Draw(img)
            
            try:
                font_large = ImageFont.truetype("arial.ttf", 36)
                font_small = ImageFont.truetype("arial.ttf", 24)
            except:
                font_large = ImageFont.load_default()
                font_small = font_large
            
            title = f"Scene {img_number}"
            draw.text((width//2, height//2 - 50), title, fill=(255, 255, 255), font=font_large, anchor="mm")
            
            wrapped_prompt = prompt[:80] + "..." if len(prompt) > 80 else prompt
            draw.text((width//2, height//2 + 20), wrapped_prompt, fill=(180, 180, 180), font=font_small, anchor="mm")
            
            draw.text((width//2, height - 100), "Image generation temporarily unavailable", fill=(100, 100, 100), font=font_small, anchor="mm")
            
            img.save(filename, "JPEG", quality=85)
            print(f"[Placeholder] Created placeholder for image {img_number}")
            logger.info(f"Created placeholder image for scene {img_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to create placeholder: {e}")
            return False

    def _generate_with_prodia(self, prompt, img_number, filename, model_idx=0):
        """Generate image using Prodia SDXL API"""
        model = SDXL_MODELS[model_idx % len(SDXL_MODELS)]
        
        # Request payload for SDXL
        payload = {
            "model": model,
            "prompt": f"high quality, photorealistic, {prompt}",
            "negative_prompt": "blurry, low quality, distorted, deformed, ugly, bad anatomy, watermark, text, logo",
            "steps": 25,
            "cfg_scale": 7,
            "seed": -1,  # Random seed
            "sampler": "DPM++ 2M Karras",
            "width": 768,
            "height": 1344,  # 9:16 aspect ratio (close to 720x1280)
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        # Step 1: Submit generation job
        print(f"[Prodia] Submitting job for image {img_number}...")
        response = requests.post(PRODIA_GENERATE_URL, json=payload, headers=headers, timeout=TIMEOUT)
        
        if response.status_code != 200:
            raise Exception(f"Failed to submit job: HTTP {response.status_code}")
        
        job_data = response.json()
        job_id = job_data.get("job")
        
        if not job_id:
            raise Exception("No job ID returned from API")
        
        print(f"[Prodia] Job {job_id} submitted, waiting for completion...")
        
        # Step 2: Poll for job completion
        for poll_attempt in range(MAX_POLL_ATTEMPTS):
            time.sleep(POLL_INTERVAL)
            
            status_response = requests.get(f"{PRODIA_JOB_URL}/{job_id}", headers=headers, timeout=TIMEOUT)
            
            if status_response.status_code != 200:
                continue
            
            status_data = status_response.json()
            status = status_data.get("status")
            
            if status == "succeeded":
                image_url = status_data.get("imageUrl")
                if not image_url:
                    raise Exception("Job succeeded but no image URL returned")
                
                # Download the image
                print(f"[Prodia] Downloading generated image...")
                img_response = requests.get(image_url, timeout=TIMEOUT)
                
                if img_response.status_code != 200:
                    raise Exception(f"Failed to download image: HTTP {img_response.status_code}")
                
                # Validate and save image
                img = Image.open(BytesIO(img_response.content))
                
                # Resize to target dimensions (720x1280)
                img = img.resize((720, 1280), Image.Resampling.LANCZOS)
                img.save(filename, "JPEG", quality=90)
                
                return True
                
            elif status == "failed":
                raise Exception(f"Job failed: {status_data.get('error', 'Unknown error')}")
            
            # Still processing, continue polling
            if poll_attempt % 5 == 0:
                print(f"[Prodia] Still generating... ({poll_attempt * POLL_INTERVAL}s elapsed)")
        
        raise Exception("Job timed out - took too long to generate")

    def download_image(self, prompt, img_number):
        """Download image with retry logic"""
        filename = os.path.join(models_config.SAVE_IMAGES_TO, f"image_{img_number}.jpg")
        ensure_save_directory(filename)

        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"\n[Prodia] Image {img_number} | Attempt {attempt}/{MAX_RETRIES}")
                logger.info(f"Attempting image {img_number}, attempt {attempt}")
                
                success = self._generate_with_prodia(prompt, img_number, filename, model_idx=attempt-1)
                
                if success:
                    print(f"[OK] Image {img_number} saved successfully")
                    logger.info(f"Image {img_number} saved successfully")
                    self.successful_images.append(img_number)
                    return True

            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                print(f"[TIMEOUT] Image {img_number}: Request timed out")
                
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {str(e)[:50]}"
                print(f"[CONNECTION] Image {img_number}: {last_error}")
                
            except Exception as e:
                last_error = str(e)
                print(f"[ERROR] Image {img_number}: {e}")

            if attempt < MAX_RETRIES:
                wait_time = INITIAL_DELAY * attempt
                print(f"[RETRY] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        # All attempts failed - create placeholder
        print(f"[FAILED] Image {img_number} failed after all retries")
        logger.warning(f"Image {img_number} failed, creating placeholder. Last error: {last_error}")
        
        if self._create_placeholder_image(prompt, img_number, filename):
            self.failed_images.append(img_number)
            return True
        
        return False

    def generate_images_from_script(self, script_lines):
        self.failed_images = []
        self.successful_images = []
        
        for i, line in enumerate(script_lines, start=1):
            print(f"\n{'='*50}")
            print(f"[IMAGE] Generating {i}/{len(script_lines)}")
            prompt = self.generate_image_prompt(line)
            print(f"[PROMPT] {prompt[:100]}...")

            self.download_image(prompt, i)
            
            # Rate limiting
            if i < len(script_lines):
                time.sleep(3)
        
        # Summary
        print(f"\n{'='*50}")
        print(f"[SUMMARY] Image Generation Complete")
        print(f"  - Successful: {len(self.successful_images)}/{len(script_lines)}")
        print(f"  - Placeholders: {len(self.failed_images)}")
        
        if self.failed_images:
            print(f"  - Failed images replaced with placeholders: {self.failed_images}")
            logger.warning(f"Some images used placeholders: {self.failed_images}")
        
        print(f"{'='*50}\n")
