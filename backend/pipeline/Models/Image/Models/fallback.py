import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import requests
import time
import logging
import hashlib
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from urllib.parse import quote

# Import the module to access dynamically overridden paths
import Models.config as models_config
from Models.Image.utils import ensure_save_directory

logger = logging.getLogger(__name__)

# Configuration
MAX_RETRIES = 2
TIMEOUT = 60
DELAY_BETWEEN_IMAGES = 2

# Optional API keys (set in environment variables)
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')


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
        text = text.split(".")[0]
        text = text[:250]
        return text.strip()

    def _extract_keywords(self, prompt):
        """Extract relevant keywords from prompt for image search"""
        # Remove common words and clean up
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'again', 'further', 'then', 'once',
                     'here', 'there', 'when', 'where', 'why', 'how', 'all',
                     'each', 'few', 'more', 'most', 'other', 'some', 'such',
                     'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
                     'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
                     'until', 'while', 'this', 'that', 'these', 'those', 'it',
                     'its', 'image', 'photo', 'picture', 'high', 'quality',
                     'detailed', 'photorealistic', 'realistic', 'beautiful',
                     'showing', 'featuring', 'depicts', 'illustrating'}
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', prompt.lower())
        keywords = [w for w in words if w not in stop_words]
        
        # Return top keywords
        return keywords[:5]

    def _prompt_to_seed(self, prompt, img_number):
        """Convert prompt to a consistent seed number"""
        hash_input = f"{prompt}_{img_number}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        return int(hash_value[:8], 16) % 1000  # Return value between 0-999

    def _create_styled_placeholder(self, prompt, img_number, filename):
        """Create a visually appealing placeholder with gradient and text"""
        try:
            width, height = 720, 1280
            
            # Create base image with gradient
            img = Image.new('RGB', (width, height), color=(25, 25, 35))
            draw = ImageDraw.Draw(img)
            
            # Create a nice gradient based on prompt hash
            seed = self._prompt_to_seed(prompt, img_number)
            
            # Color schemes based on seed
            color_schemes = [
                ((30, 50, 80), (60, 30, 70)),    # Blue to purple
                ((50, 70, 40), (30, 50, 60)),    # Green to teal
                ((80, 50, 30), (60, 40, 50)),    # Orange to mauve
                ((40, 40, 60), (50, 30, 40)),    # Indigo to maroon
                ((60, 60, 40), (40, 50, 60)),    # Olive to slate
            ]
            
            start_color, end_color = color_schemes[seed % len(color_schemes)]
            
            # Draw gradient
            for y in range(height):
                ratio = y / height
                r = int(start_color[0] + (end_color[0] - start_color[0]) * ratio)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * ratio)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * ratio)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # Add some visual interest - circles/shapes
            for i in range(5):
                cx = (seed * (i + 1) * 73) % width
                cy = (seed * (i + 1) * 97) % height
                radius = 50 + (seed * (i + 1)) % 150
                alpha_color = (255, 255, 255, 15)
                
                # Draw semi-transparent circles
                overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                overlay_draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], 
                                    fill=(255, 255, 255, 10))
                img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            
            draw = ImageDraw.Draw(img)
            
            # Load fonts
            try:
                font_large = ImageFont.truetype("arial.ttf", 48)
                font_medium = ImageFont.truetype("arial.ttf", 28)
                font_small = ImageFont.truetype("arial.ttf", 20)
            except:
                font_large = ImageFont.load_default()
                font_medium = font_large
                font_small = font_large
            
            # Add scene number
            title = f"Scene {img_number}"
            draw.text((width//2, height//2 - 80), title, fill=(255, 255, 255), 
                     font=font_large, anchor="mm")
            
            # Add keywords from prompt
            keywords = self._extract_keywords(prompt)
            if keywords:
                keyword_text = " • ".join(keywords[:3])
                draw.text((width//2, height//2), keyword_text, fill=(200, 200, 200), 
                         font=font_medium, anchor="mm")
            
            # Add brief prompt
            wrapped_prompt = prompt[:60] + "..." if len(prompt) > 60 else prompt
            draw.text((width//2, height//2 + 60), wrapped_prompt, fill=(150, 150, 150), 
                     font=font_small, anchor="mm")
            
            # Add subtle note at bottom
            draw.text((width//2, height - 80), "Visual placeholder", 
                     fill=(80, 80, 80), font=font_small, anchor="mm")
            
            img.save(filename, "JPEG", quality=90)
            print(f"[Placeholder] Created styled placeholder for image {img_number}")
            logger.info(f"Created placeholder image for scene {img_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to create placeholder: {e}")
            return False

    def _try_picsum(self, prompt, img_number, filename):
        """Get a real photo from Picsum with prompt-based seed"""
        seed = self._prompt_to_seed(prompt, img_number)
        
        # Picsum provides random photos - use seed for consistency
        url = f'https://picsum.photos/seed/{seed}/720/1280'
        
        response = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        
        if response.status_code != 200:
            raise Exception(f"Picsum HTTP {response.status_code}")
        
        if len(response.content) < 10000:
            raise Exception("Image too small")
        
        # Validate and save
        img = Image.open(BytesIO(response.content))
        
        # Apply subtle enhancements to make it more visually appealing
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.1)
        
        img.save(filename, "JPEG", quality=90)
        return True

    def _try_pexels(self, prompt, img_number, filename):
        """Try Pexels API (requires API key)"""
        if not PEXELS_API_KEY:
            raise Exception("No Pexels API key configured")
        
        keywords = self._extract_keywords(prompt)
        query = quote(' '.join(keywords[:3]) if keywords else 'nature')
        
        url = f'https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=portrait'
        
        headers = {
            'Authorization': PEXELS_API_KEY
        }
        
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        
        if response.status_code != 200:
            raise Exception(f"Pexels HTTP {response.status_code}")
        
        data = response.json()
        photos = data.get('photos', [])
        
        if not photos:
            raise Exception("No photos found")
        
        # Select photo based on img_number for variety
        photo = photos[img_number % len(photos)]
        photo_url = photo.get('src', {}).get('large2x') or photo.get('src', {}).get('large')
        
        if not photo_url:
            raise Exception("No photo URL")
        
        img_response = requests.get(photo_url, timeout=TIMEOUT)
        if img_response.status_code != 200:
            raise Exception(f"Failed to download photo")
        
        img = Image.open(BytesIO(img_response.content))
        img = img.resize((720, 1280), Image.Resampling.LANCZOS)
        img.save(filename, "JPEG", quality=90)
        
        return True

    def _try_pollinations(self, prompt, img_number, filename):
        """Try Pollinations API (free AI images)"""
        safe_prompt = quote(prompt[:150])
        seed = self._prompt_to_seed(prompt, img_number)
        
        # Try different models
        models = ['flux', 'turbo']
        model = models[img_number % len(models)]
        
        url = f'https://image.pollinations.ai/prompt/{safe_prompt}?width=720&height=1280&seed={seed}&model={model}&nologo=true'
        
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code != 200:
            raise Exception(f"Pollinations HTTP {response.status_code}")
        
        content_type = response.headers.get('Content-Type', '')
        if 'image' not in content_type:
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

    def download_image(self, prompt, img_number):
        """Download image using multiple fallback methods"""
        filename = os.path.join(models_config.SAVE_IMAGES_TO, f"image_{img_number}.jpg")
        ensure_save_directory(filename)

        # Methods to try in order of preference
        methods = [
            ("Pollinations", lambda: self._try_pollinations(prompt, img_number, filename)),
            ("Pexels", lambda: self._try_pexels(prompt, img_number, filename)),
            ("Picsum", lambda: self._try_picsum(prompt, img_number, filename)),
        ]

        for method_name, method_func in methods:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    print(f"\n[{method_name}] Image {img_number} | Attempt {attempt}/{MAX_RETRIES}")
                    logger.info(f"Trying {method_name} for image {img_number}, attempt {attempt}")
                    
                    success = method_func()
                    
                    if success:
                        print(f"[OK] Image {img_number} saved via {method_name}")
                        logger.info(f"Image {img_number} saved via {method_name}")
                        self.successful_images.append(img_number)
                        return True

                except requests.exceptions.Timeout:
                    print(f"[TIMEOUT] {method_name}: Request timed out")
                    
                except requests.exceptions.ConnectionError as e:
                    print(f"[CONNECTION] {method_name}: Connection error")
                    
                except Exception as e:
                    error_msg = str(e)[:80]
                    print(f"[ERROR] {method_name}: {error_msg}")
                    
                    # Skip Pexels if no API key
                    if "No Pexels API key" in str(e):
                        break

                if attempt < MAX_RETRIES:
                    time.sleep(1)
            
            time.sleep(0.5)

        # All methods failed - create styled placeholder
        print(f"[FALLBACK] Creating styled placeholder for image {img_number}")
        logger.warning(f"Image {img_number} using placeholder")
        
        if self._create_styled_placeholder(prompt, img_number, filename):
            self.failed_images.append(img_number)
            return True
        
        return False

    def generate_images_from_script(self, script_lines):
        self.failed_images = []
        self.successful_images = []
        
        print(f"\n{'='*50}")
        print(f"[IMAGE GENERATOR] Starting image generation")
        print(f"  - Total images: {len(script_lines)}")
        print(f"  - Pexels API: {'Configured' if PEXELS_API_KEY else 'Not configured'}")
        print(f"{'='*50}")
        
        for i, line in enumerate(script_lines, start=1):
            print(f"\n{'='*50}")
            print(f"[IMAGE] Generating {i}/{len(script_lines)}")
            prompt = self.generate_image_prompt(line)
            print(f"[PROMPT] {prompt[:80]}...")

            self.download_image(prompt, i)
            
            if i < len(script_lines):
                time.sleep(DELAY_BETWEEN_IMAGES)
        
        # Summary
        print(f"\n{'='*50}")
        print(f"[SUMMARY] Image Generation Complete")
        print(f"  - Successful: {len(self.successful_images)}/{len(script_lines)}")
        print(f"  - Placeholders: {len(self.failed_images)}")
        
        if self.failed_images:
            print(f"  - Placeholder images: {self.failed_images}")
        
        print(f"{'='*50}\n")
