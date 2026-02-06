import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import requests
import time
import logging
from urllib.parse import quote
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Import the module to access dynamically overridden paths
import Models.config as models_config
from Models.Image.utils import ensure_save_directory

logger = logging.getLogger(__name__)

# Configuration - Optimized for faster fallback when API is down
MAX_RETRIES = 3
INITIAL_DELAY = 2
BACKOFF_FACTOR = 1.5
TIMEOUT = 30
MIN_IMAGE_SIZE = 5_000  # Reduced threshold for smaller valid images

# Alternative API endpoints to try (reduced for speed)
POLLINATIONS_MODELS = ["flux", "turbo"]


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

        # Simplify + cap prompt
        text = text.split(".")[0]          # take first sentence only
        text = text[:200]                  # hard limit
        return text.strip()

    def _create_placeholder_image(self, prompt, img_number, filename):
        """Create a placeholder image when API fails - ensures video can still be generated"""
        try:
            # Create a gradient background placeholder
            width, height = 720, 1280
            img = Image.new('RGB', (width, height), color=(30, 30, 40))
            draw = ImageDraw.Draw(img)
            
            # Add a subtle gradient effect
            for y in range(height):
                r = int(30 + (y / height) * 20)
                g = int(30 + (y / height) * 15)
                b = int(40 + (y / height) * 25)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # Add text
            draw = ImageDraw.Draw(img)
            
            # Try to use a system font, fall back to default
            try:
                font_large = ImageFont.truetype("arial.ttf", 36)
                font_small = ImageFont.truetype("arial.ttf", 24)
            except:
                font_large = ImageFont.load_default()
                font_small = font_large
            
            # Center text
            title = f"Scene {img_number}"
            draw.text((width//2, height//2 - 50), title, fill=(255, 255, 255), font=font_large, anchor="mm")
            
            # Wrap prompt text
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

    def _try_download_with_model(self, prompt, img_number, filename, model, width=720, height=1280):
        """Try downloading image with a specific model"""
        safe_prompt = quote(prompt)
        seed = 42 + img_number  # Vary seed per image for diversity
        
        image_url = (
            f"https://image.pollinations.ai/prompt/{safe_prompt}"
            f"?width={width}&height={height}&seed={seed}&model={model}&nologo=true"
        )
        
        response = requests.get(image_url, timeout=TIMEOUT)
        
        if response.status_code == 502:
            raise Exception(f"502 Bad Gateway - Service temporarily unavailable")
        elif response.status_code == 503:
            raise Exception(f"503 Service Unavailable - API overloaded")
        elif response.status_code == 429:
            raise Exception(f"429 Rate Limited - Too many requests")
        elif response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type:
            raise Exception(f"Not an image response (got {content_type})")
        
        if len(response.content) < MIN_IMAGE_SIZE:
            raise Exception(f"Image too small ({len(response.content)} bytes)")
        
        # Validate image can be opened
        img = Image.open(BytesIO(response.content))
        img.verify()
        
        with open(filename, "wb") as f:
            f.write(response.content)
        
        return True

    def download_image(self, prompt, img_number):
        """Download image with robust retry logic and fallback mechanisms"""
        filename = os.path.join(models_config.SAVE_IMAGES_TO, f"image_{img_number}.jpg")
        ensure_save_directory(filename)

        delay = INITIAL_DELAY
        last_error = None

        # Try each model with retries
        for model_idx, model in enumerate(POLLINATIONS_MODELS):
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    print(f"\n[Pollinations] Image {img_number} | Model: {model} | Attempt {attempt}/{MAX_RETRIES}")
                    logger.info(f"Attempting image {img_number} with model {model}, attempt {attempt}")
                    
                    success = self._try_download_with_model(prompt, img_number, filename, model)
                    
                    if success:
                        print(f"[OK] Image {img_number} saved successfully")
                        logger.info(f"Image {img_number} saved successfully with model {model}")
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

                # Exponential backoff with jitter
                if attempt < MAX_RETRIES:
                    jitter = (img_number % 3) + 1  # Add some jitter
                    wait_time = min(delay + jitter, 15)  # Cap at 15 seconds max
                    print(f"[RETRY] Waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
                    delay = min(delay * BACKOFF_FACTOR, 15)  # Cap at 15 seconds

            # Reset delay for next model
            delay = INITIAL_DELAY
            
            # If not last model, try next one
            if model_idx < len(POLLINATIONS_MODELS) - 1:
                print(f"[FALLBACK] Trying next model...")
                time.sleep(2)

        # All attempts failed - create placeholder
        print(f"[FAILED] Image {img_number} failed after all retries")
        logger.warning(f"Image {img_number} failed, creating placeholder. Last error: {last_error}")
        
        # Create placeholder so video generation can continue
        if self._create_placeholder_image(prompt, img_number, filename):
            self.failed_images.append(img_number)
            return True  # Return True because we have a placeholder
        
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
            
            # Rate limiting - be nice to the API
            if i < len(script_lines):
                time.sleep(5)
        
        # Summary
        print(f"\n{'='*50}")
        print(f"[SUMMARY] Image Generation Complete")
        print(f"  - Successful: {len(self.successful_images)}/{len(script_lines)}")
        print(f"  - Placeholders: {len(self.failed_images)}")
        
        if self.failed_images:
            print(f"  - Failed images replaced with placeholders: {self.failed_images}")
            logger.warning(f"Some images used placeholders: {self.failed_images}")
        
        print(f"{'='*50}\n")