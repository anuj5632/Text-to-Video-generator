import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
sys.dont_write_bytecode = True

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    concatenate_videoclips
)

from Models.Animations.animations_factory import load_animation_model
from Models.Video.utils import (
    ensure_directories,
    verify_assets,
    transcribe_audio_with_script,
    crop_to_portrait
)
# Import the module itself so we can access dynamically overridden values
import Models.config as models_config
from config import VIDEO_MODEL_CONFIG


class VideoGenerator:
    def __init__(self):
        # Access audio_file dynamically in generate_video, not at init time
        ensure_directories()
        self.animation = load_animation_model()
        self.config = VIDEO_MODEL_CONFIG

    def generate_video(self, topic=None):
        print(f"🎬 Starting video generation with config: {self.config}...")

        # 1. Transcribe audio → timestamps
        # Access config values dynamically to pick up runtime overrides
        timestamps = transcribe_audio_with_script(
            audio_file=models_config.SAVE_VOICEOVER_TO,
            script_file=models_config.SAVE_SCRIPT_TO,
            output_file=models_config.SAVE_TIMESTAMPS_TO
        )

        if not verify_assets(timestamps, models_config.SAVE_VOICEOVER_TO, models_config.SAVE_IMAGES_TO):
            print("⚠️ Some assets missing, continuing with available ones...")

        image_clips = []

        # 2. Create clips per timestamp
        for i, segment in enumerate(timestamps, start=1):
            image_path = os.path.join(models_config.SAVE_IMAGES_TO, f"image_{i}.jpg")

            if not os.path.exists(image_path):
                print(f"⚠️ Missing image {image_path}, skipping")
                continue

            duration = max(segment["end"] - segment["start"], 0.5)

            clip = (
                ImageClip(image_path)
                .set_duration(duration)
                .resize(1.1)
            )

            clip = crop_to_portrait(clip)
            clip = self.animation.apply(clip, zoom_in=(i % 2 == 1))
            image_clips.append(clip)

        if not image_clips:
            raise RuntimeError("❌ No image clips available to create video")

        # 3. Combine clips
        video = concatenate_videoclips(image_clips, method="compose")

        # 4. Attach audio (VERY IMPORTANT)
        audio = AudioFileClip(models_config.SAVE_VOICEOVER_TO)
        video = video.set_audio(audio)
        video = video.set_duration(audio.duration)
        video = video.set_fps(models_config.VIDEO_FPS)
        print("video and audio combined successfully")

        # 5. Render
        output_path = models_config.SAVE_VIDEO_TO
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        preset = "ultrafast" if self.config == "standard" else "medium"
        threads = 4 if self.config == "standard" else 8

        print(f"⏳ Rendering video to {output_path}...")

        video.write_videofile(
            output_path,
            fps=models_config.VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            preset=preset,
            threads=threads,
            verbose=False,
            logger=None
        )

        print(f"✅ Video saved at {output_path}")
        return output_path
