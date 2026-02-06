import sys
import os
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
# Import the module to access dynamically overridden paths
import Models.config as models_config
from config import AUDIO_MODEL_VOICE
from Models.utils import ensure_save_directory

class VoiceOverGenerator:
    def __init__(self):
        # Don't ensure directory at init time - path may be overridden later
        pass

    def generate_voiceover(self, text):
        # Access path dynamically to get runtime-overridden value
        save_path = models_config.SAVE_VOICEOVER_TO
        ensure_save_directory(save_path)
        
        url = "https://www.openai.fm/api/generate"
        payload = {
            "input": text,
            "voice": AUDIO_MODEL_VOICE,
            "vibe": "null"
        }
        files = {key: (None, value) for key, value in payload.items()}
        response = requests.post(url, files=files)

        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Audio file saved at {save_path}")
            return save_path
        else:
            print("❌ Error:", response.status_code, response.text)
            return None


if __name__ == "__main__":
    generator = VoiceOverGenerator()
    text = input("Enter text for voiceover: ")
    generator.generate_voiceover(text)
