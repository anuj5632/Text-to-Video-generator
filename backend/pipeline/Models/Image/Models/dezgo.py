import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import requests
import time
import logging
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import quote

# Import the module to access dynamically overridden paths
import Models.config as models_config
from Models.Image.utils import ensure_save_directory

logger = logging.getLogger(__name__)

# Configuration
MAX_RETRIES = 2
TIMEOUT = 90
DELAY_BETWEEN_IMAGES = 3


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
        
        # Clean and optimize prompt
        text = text.split(".")[0]  # take first sentence
        text = text[:250]  # reasonable limit
        return text.strip()

    def _create_placeholder_image(self, prompt, img_number, filename):
        """Create a placeholder image when all APIs fail"""
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

    def _try_dezgo(self, prompt, filename):
        """Try generating image using Dezgo API (free, no API key)"""
        url = "https://api.dezgo.com/text2image"
        
        payload = {
            "prompt": f"high quality, detailed, {prompt}",
            "negative_prompt": "blurry, low quality, distorted, deformed, ugly, bad anatomy, watermark, text, logo, nsfw",
            "model": "sdxl",
            "width": 768,
            "height": 1344,
            "sampler": "dpmpp_2m_karras",
            "steps": 30,
            "guidance": 7.5,
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        response = requests.post(url, data=payload, headers=headers, timeout=TIMEOUT)
        
        if response.status_code != 200:
            raise Exception(f"Dezgo API error: HTTP {response.status_code}")
        
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type:
            raise Exception(f"Dezgo returned non-image content: {content_type}")
        
        # Validate and resize image
        img = Image.open(BytesIO(response.content))
        img = img.resize((720, 1280), Image.Resampling.LANCZOS)
        img.save(filename, "JPEG", quality=90)
        
        return True

    def _try_segmind(self, prompt, filename):
        """Try generating image using Segmind free API"""
        url = "https://api.segmind.com/v1/sdxl1.0-txt2img"
        
        payload = {
            "prompt": f"high quality, photorealistic, {prompt}",
            "negative_prompt": "blurry, low quality, distorted, watermark, text",
            "samples": 1,
            "scheduler": "UniPC",
            "num_inference_steps": 25,
            "guidance_scale": 7.5,
            "seed": -1,
            "img_width": 768,
            "img_height": 1344,
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        
        if response.status_code != 200:
            raise Exception(f"Segmind API error: HTTP {response.status_code}")
        
        content_type = response.headers.get("Content-Type", "")
        if "image" in content_type:
            img = Image.open(BytesIO(response.content))
            img = img.resize((720, 1280), Image.Resampling.LANCZOS)
            img.save(filename, "JPEG", quality=90)
            return True
        else:
            raise Exception(f"Segmind returned non-image: {content_type}")

    def _try_pollinations_simple(self, prompt, img_number, filename):
        """Try Pollinations with minimal parameters"""
        safe_prompt = quote(prompt[:150])
        seed = 42 + img_number
        
        # Simple direct URL approach
        image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=720&height=1280&seed={seed}&nologo=true"
        
        response = requests.get(image_url, timeout=TIMEOUT)
        
        if response.status_code != 200:
            raise Exception(f"Pollinations HTTP {response.status_code}")
        
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type:
            raise Exception(f"Not an image: {content_type}")
        
        if len(response.content) < 5000:
            raise Exception(f"Image too small: {len(response.content)} bytes")
        
        # Validate image
        img = Image.open(BytesIO(response.content))
        img.verify()
        
        # Re-open and save
        img = Image.open(BytesIO(response.content))
        img = img.resize((720, 1280), Image.Resampling.LANCZOS)
        img.save(filename, "JPEG", quality=90)
        
        return True

    def _try_getimgai_free(self, prompt, filename):
        """Try GetImg.ai demo endpoint"""
        url = "https://api.getimg.ai/v1/stable-diffusion-xl/text-to-image"
        
        payload = {
            "prompt": f"high quality, {prompt}",
            "negative_prompt": "blurry, low quality, watermark",
            "width": 768,
            "height": 1344,
            "steps": 25,
            "guidance": 7.5,
            "output_format": "jpeg",
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        
        if response.status_code != 200:
            raise Exception(f"GetImg.ai API error: HTTP {response.status_code}")
        
        data = response.json()
        image_b64 = data.get("image")
        
        if not image_b64:
            raise Exception("No image in response")
        
        img_data = base64.b64decode(image_b64)
        img = Image.open(BytesIO(img_data))
        img = img.resize((720, 1280), Image.Resampling.LANCZOS)
        img.save(filename, "JPEG", quality=90)
        
        return True

    def _try_picfinder(self, prompt, filename):
        """Try PicFinder AI (free image generation)"""
        url = "https://api.picfinder.ai/v1/generate"
        
        payload = {
            "prompt": prompt,
            "width": 720,
            "height": 1280,
        }
        
        response = requests.post(url, json=payload, timeout=TIMEOUT)
        
        if response.status_code != 200:
            raise Exception(f"PicFinder API error: HTTP {response.status_code}")
        
        data = response.json()
        image_url = data.get("image_url") or data.get("url")
        
        if not image_url:
            raise Exception("No image URL in response")
        
        img_response = requests.get(image_url, timeout=TIMEOUT)
        if img_response.status_code != 200:
            raise Exception(f"Failed to download: HTTP {img_response.status_code}")
        
        img = Image.open(BytesIO(img_response.content))
        img = img.resize((720, 1280), Image.Resampling.LANCZOS)
        img.save(filename, "JPEG", quality=90)
        
        return True

    def download_image(self, prompt, img_number):
        """Download image using multiple API fallbacks"""
        filename = os.path.join(models_config.SAVE_IMAGES_TO, f"image_{img_number}.jpg")
        ensure_save_directory(filename)

        # List of methods to try in order
        methods = [
            ("Dezgo", lambda: self._try_dezgo(prompt, filename)),
            ("Pollinations", lambda: self._try_pollinations_simple(prompt, img_number, filename)),
        ]

        for method_name, method_func in methods:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    print(f"\n[{method_name}] Image {img_number} | Attempt {attempt}/{MAX_RETRIES}")
                    logger.info(f"Trying {method_name} for image {img_number}, attempt {attempt}")
                    
                    success = method_func()
                    
                    if success:
                        print(f"[OK] Image {img_number} saved successfully via {method_name}")
                        logger.info(f"Image {img_number} saved via {method_name}")
                        self.successful_images.append(img_number)
                        return True

                except requests.exceptions.Timeout:
                    print(f"[TIMEOUT] {method_name}: Request timed out")
                    
                except requests.exceptions.ConnectionError as e:
                    print(f"[CONNECTION] {method_name}: Connection error")
                    logger.warning(f"{method_name} connection error: {str(e)[:100]}")
                    
                except Exception as e:
                    print(f"[ERROR] {method_name}: {str(e)[:100]}")
                    logger.warning(f"{method_name} error: {str(e)[:200]}")

                if attempt < MAX_RETRIES:
                    time.sleep(2)
            
            # Try next method
            print(f"[FALLBACK] {method_name} failed, trying next method...")
            time.sleep(1)

        # All methods failed - create placeholder
        print(f"[FAILED] Image {img_number} - all methods failed, creating placeholder")
        logger.warning(f"Image {img_number} failed with all methods, creating placeholder")
        
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
            
            # Rate limiting between images
            if i < len(script_lines):
                time.sleep(DELAY_BETWEEN_IMAGES)
        
        # Summary
        print(f"\n{'='*50}")
        print(f"[SUMMARY] Image Generation Complete")
        print(f"  - Successful: {len(self.successful_images)}/{len(script_lines)}")
        print(f"  - Placeholders: {len(self.failed_images)}")
        
        if self.failed_images:
            print(f"  - Failed images: {self.failed_images}")
            logger.warning(f"Some images used placeholders: {self.failed_images}")
        
        print(f"{'='*50}\n")
