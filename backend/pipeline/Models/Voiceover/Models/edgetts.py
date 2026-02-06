import sys
import os
import asyncio
import edge_tts
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
# Import the module to access dynamically overridden paths
import Models.config as models_config
from config import AUDIO_MODEL_VOICE
from Models.utils import ensure_save_directory

class VoiceOverGenerator:
    def __init__(self):
        # Don't ensure directory at init time - path may be overridden later
        pass

    async def text_to_audio(self, text):
        # Access path dynamically to get runtime-overridden value
        save_path = models_config.SAVE_VOICEOVER_TO
        ensure_save_directory(save_path)
        communicate = edge_tts.Communicate(text, AUDIO_MODEL_VOICE)
        await communicate.save(save_path)
        print(f"✅ Audio file saved at {save_path}")
        return save_path

    def generate_voiceover(self, text):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.text_to_audio(text))
        finally:
            loop.close()
        return result


if __name__ == "__main__":
    generator = VoiceOverGenerator()
    text = input("Enter text for voiceover: ")
    generator.generate_voiceover(text)
