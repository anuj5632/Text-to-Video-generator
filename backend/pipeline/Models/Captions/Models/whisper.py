# Models/Captions/Models/whisper.py
import whisper
import torch
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
sys.dont_write_bytecode = True

from Models.config import SAVE_TIMESTAMPS_TO, SAVE_VOICEOVER_TO
from Models.Captions.caption_processor import process_video as process_with_captions
from Models.Captions.utils import get_available_caption_styles, get_available_fonts
from config import CAPTION_STYLE, CAPTION_MODEL_TYPE

class CaptionGenerator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # NOTE: removed compute_type because whisper.load_model may not accept it
        self.whisper_model = whisper.load_model(CAPTION_MODEL_TYPE, device=self.device)

    def generate_word_timestamps(self, audio_path, output_json=SAVE_TIMESTAMPS_TO):
        """Generate word-level (or segment-level) timestamps using Whisper (safe fallback)."""
        if not os.path.exists(audio_path):
            print(f"❌ Audio file not found: {audio_path}")
            return None

        print("⏳ Transcribing audio (this may take a while)...")
        # Try to request word-level timestamps; if unsupported, fall back to segment-level
        try:
            # Some whisper backends support word_timestamps=True (or return words in segments)
            result = self.whisper_model.transcribe(audio_path, word_timestamps=True)
        except TypeError:
            # fallback: older whisper API may not accept word_timestamps arg
            result = self.whisper_model.transcribe(audio_path)

        words_data = []

        # Preferred: result["segments"] contains words inside each segment
        segments = result.get("segments", [])
        for seg in segments:
            # If 'words' present (word-level timestamps), use them
            if "words" in seg and seg["words"]:
                for w in seg["words"]:
                    # Some implementations use 'word' or 'text'
                    txt = w.get("word") or w.get("text") or w.get("word_str") or ""
                    if "start" in w and "end" in w:
                        words_data.append({"start": w["start"], "end": w["end"], "text": txt})
            else:
                # fallback: use segment-level timestamps (one entry per segment)
                txt = seg.get("text", "").strip()
                if "start" in seg and "end" in seg:
                    words_data.append({"start": seg["start"], "end": seg["end"], "text": txt})

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(words_data, f, indent=4)

        print(f"✅ Timestamps saved to {output_json} ({len(words_data)} items)")
        return output_json

    def process_video(self, video_path, style_name=None, output_path=None):
        if style_name is None:
            style_name = CAPTION_STYLE
        return process_with_captions(self, video_path, style_name, output_path)

    def get_available_styles(self):
        styles = get_available_caption_styles()
        print(f"\n📚 Available caption styles:")
        for style in styles:
            marker = "✓" if style == CAPTION_STYLE else " "
            print(f" [{marker}] {style}")
        return styles

    def get_available_fonts(self):
        fonts = get_available_fonts()
        print(f"\n🔠 Available fonts:")
        for font in fonts:
            print(f" - {font}")
        return fonts

if __name__ == "__main__":
    caption_generator = CaptionGenerator()
    available_styles = caption_generator.get_available_styles()
    available_fonts = caption_generator.get_available_fonts()
    video_path = input("\nEnter video path: ")
    print(f"Using caption style: {CAPTION_STYLE}")
    use_different_style = input(f"Would you like to use a different style? (y/n): ").lower() == 'y'
    if use_different_style and available_styles:
        style_name = input(f"Enter style name ({', '.join(available_styles)}): ") or CAPTION_STYLE
    else:
        style_name = CAPTION_STYLE
    caption_generator.process_video(video_path, style_name)
