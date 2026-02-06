
try:
    from PIL import Image
   
    if not hasattr(Image, "ANTIALIAS"):
        Image.ANTIALIAS = Image.Resampling.LANCZOS
    if not hasattr(Image, "BICUBIC"):
        Image.BICUBIC = Image.Resampling.BICUBIC
    if not hasattr(Image, "BILINEAR"):
        Image.BILINEAR = Image.Resampling.BILINEAR
except Exception:
   
    pass


import sys
import os
import shutil
import logging
import traceback
import argparse
from pathlib import Path
import json
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("generation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.dont_write_bytecode = True

from Models.Script.script_factory import load_script_model
from Models.Voiceover.voiceover_factory import load_voiceover_model
from Models.Image.image_factory import load_image_model
from Models.Video.video_factory import load_video_model
from Models.Captions.captions_factory import load_caption_model
from Models.Script.utils import save_formatted_script
from Models.Image.utils import format_for_image_prompt
import Models.config as models_config  
from config import CAPTION_MODEL, CAPTION_STYLE
from progress_tracker import ProgressTracker, Stage


def write_status(job_dir, progress=0, stage="", message=""):
    try:
        status_path = os.path.join(job_dir, "status.json")
        payload = {
            "progress": progress,
            "stage": stage,
            "message": message,
            "timestamp": time.time()
        }
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        logger.exception("Failed to write status.json")

def _override_save_paths(job_dir):
    """
    Override the SAVE_* variables in Models.config so all outputs go into job_dir.
    This assumes Models.config defines: SAVE_SCRIPT_TO, SAVE_IMAGES_TO, SAVE_VOICEOVER_TO,
    SAVE_TIMESTAMPS_TO, SAVE_VIDEO_TO, VIDEO_FPS, VIDEO_RATIO, etc.
    """
    
    script_path = os.path.join(job_dir, "Script", "Script.txt")
    images_path = os.path.join(job_dir, "Generated_Images")
    voice_path = os.path.join(job_dir, "Voiceover", "Voiceover.mp3")
    timestamps_path = os.path.join(job_dir, "Timestamps", "Timestamps.json")
    video_path = os.path.join(job_dir, "Video", "Video.mp4")

    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    os.makedirs(images_path, exist_ok=True)
    os.makedirs(os.path.dirname(voice_path), exist_ok=True)
    os.makedirs(os.path.dirname(timestamps_path), exist_ok=True)
    os.makedirs(os.path.dirname(video_path), exist_ok=True)

    try:
        models_config.SAVE_SCRIPT_TO = script_path
        models_config.SAVE_IMAGES_TO = images_path + os.sep
        models_config.SAVE_VOICEOVER_TO = voice_path
        models_config.SAVE_TIMESTAMPS_TO = timestamps_path
        models_config.SAVE_VIDEO_TO = video_path
        logger.debug("Overrode Models.config save paths to job_dir: %s", job_dir)
    except Exception:
        logger.exception("Failed to override Models.config save paths")

def clear_temp_data():
    """Clear temporary data from previous generations (legacy Data/Temp)."""
    logger.info("Clearing temporary data")
    temp_dir = Path(os.path.join(os.path.dirname(__file__), "..", "Data", "Temp"))
    if not temp_dir.exists():
        logger.debug("Temp directory does not exist, nothing to clear: %s", temp_dir)
        return

    for item in temp_dir.iterdir():
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            elif item.is_file():
                item.unlink()
        except PermissionError:
            logger.warning(f"Could not remove {item} - Permission denied")
        except Exception as e:
            logger.warning(f"Error clearing {item}: {str(e)}")

def ensure_temp_folders(base_path=None):
    """Ensure required temporary folders exist (legacy compatibility)."""
    logger.info("Ensuring temporary folders exist")
    base = base_path or os.path.join(os.path.dirname(__file__), "..", "Data", "Temp")
    for folder in ["Script", "Voiceover", "Generated_Images", "Video", "Timestamps"]:
        folder_path = Path(base) / folder
        folder_path.mkdir(parents=True, exist_ok=True)

def generate_video_from_prompt(prompt: str, job_id: str, outputs_root=None, skip_cleanup=False, no_captions=False, debug=False):
    """
    Backend-friendly entrypoint. Runs the same pipeline but writes outputs to:
      <outputs_root>/<job_id>/...
    Returns: final_video_path (str) or raises an exception.
    """
    if outputs_root is None:
       
        outputs_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))

    job_dir = os.path.join(outputs_root, job_id)
    os.makedirs(job_dir, exist_ok=True)

   
    write_status(job_dir, 1, "START", "Job initialized")

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if not skip_cleanup:
            clear_temp_data()
        ensure_temp_folders()

        # override all save paths so pipeline writes into job_dir
        _override_save_paths(job_dir)
        write_status(job_dir, 5, "INIT", "Save paths configured")

        tracker = ProgressTracker(prompt)
        write_status(job_dir, 10, "SCRIPT", "Loading script model")

        # 1. Generate Script
        tracker.update_stage(Stage.SCRIPT)
        script_generator = load_script_model()
        tracker.log_substep("Generating script...")
        write_status(job_dir, 15, "SCRIPT", "Generating script")
        script = script_generator.generate_script(prompt)
        logger.info("Generated Script snippet: %s", script[:120].replace("\n", " "))
        write_status(job_dir, 20, "SCRIPT", "Script generated")

       
        formatted_script = save_formatted_script(script, file_path=models_config.SAVE_SCRIPT_TO)

        
        tracker.update_stage(Stage.VOICEOVER)
        tracker.log_substep("Synthesizing voiceover...")
        write_status(job_dir, 25, "VOICEOVER", "Synthesizing voiceover")
        voiceover_generator = load_voiceover_model()
        audio_path = voiceover_generator.generate_voiceover(script)
        tracker.log_substep(f"Voiceover saved to: {audio_path}")
        write_status(job_dir, 35, "VOICEOVER", f"Voiceover saved: {os.path.basename(audio_path) if audio_path else 'N/A'}")

        # 3. Format script for image generation
        tracker.update_stage(Stage.IMAGE_PREP)
        tracker.log_substep("Formatting script for image generation...")
        write_status(job_dir, 40, "IMAGE_PREP", "Formatting script for image prompts")
        image_prompts = format_for_image_prompt(formatted_script)
        tracker.log_substep(f"Created {len(image_prompts)} image prompts")
        write_status(job_dir, 45, "IMAGE_PREP", f"Created {len(image_prompts)} image prompts")

        # 4. Generate Images
        tracker.update_stage(Stage.IMAGE_GEN)
        image_generator = load_image_model()
        image_paths = []
        total_images = len(image_prompts) if image_prompts else 0

        for i, prompt_line in enumerate(image_prompts, start=1):
            tracker.log_substep("Generating image", i, total_images)
            write_status(job_dir, 45 + int(30 * i / max(total_images, 1)), "IMAGE_GEN", f"Generating image {i}/{total_images}")
            try:
                # Using your existing download_image or generate method; adapt if your API differs
                image_generator.download_image(prompt_line, i)
                # path where it should have been saved (consistent with _override_save_paths)
                img_path = os.path.join(models_config.SAVE_IMAGES_TO, f"image_{i}.jpg")
                image_paths.append(img_path)
            except Exception as e:
                logger.exception("Error generating image %d: %s", i, e)
            time.sleep(1)  # keep the original pacing

        write_status(job_dir, 75, "IMAGE_GEN", f"{len(image_paths)}/{total_images} images saved")

        # 5. Generate Video
        tracker.update_stage(Stage.VIDEO)
        tracker.log_substep("Assembling video...")
        write_status(job_dir, 80, "VIDEO", "Assembling video")
        video_generator = load_video_model()
        video_path = video_generator.generate_video(prompt)  # ensure this writes to models_config.SAVE_VIDEO_TO
        write_status(job_dir, 90, "VIDEO", "Video assembled")

        # If the video generator returns a different path, copy into job_dir's video file
        expected_final = models_config.SAVE_VIDEO_TO
        if video_path and os.path.exists(video_path) and video_path != expected_final:
            try:
                shutil.copy(video_path, expected_final)
                video_path = expected_final
            except Exception:
                logger.exception("Failed copying video to expected final path")

        # 6. Add Captions if requested
        captioned_video_path = None
        if not no_captions and video_path:
            tracker.update_stage(Stage.CAPTIONS)
            tracker.log_substep(f"Adding captions using model: {CAPTION_MODEL}, style: {CAPTION_STYLE}")
            write_status(job_dir, 92, "CAPTIONS", "Starting caption generation")

            try:
                caption_generator = load_caption_model(CAPTION_MODEL)
                captioned_video_path = caption_generator.process_video(video_path, CAPTION_STYLE)
                if captioned_video_path:
                    video_path = captioned_video_path
                    write_status(job_dir, 97, "CAPTIONS", "Captions added")
                else:
                    write_status(job_dir, 97, "CAPTIONS", "Captioning returned no path")
            except Exception as e:
                logger.exception("Error during captioning: %s", e)
                write_status(job_dir, 0, "ERROR", f"Captioning failed: {str(e)}")

        # 7. Cleanup (if desired)
        if not skip_cleanup:
            tracker.update_stage(Stage.CLEANUP)
            tracker.log_substep("Cleaning up temporary files...")
            write_status(job_dir, 99, "CLEANUP", "Cleaning temporary files")
            clear_temp_data()
        else:
            tracker.log_substep("Skipping cleanup (--skip-cleanup flag)")

        # Finalize
        final_video = video_path if video_path else models_config.SAVE_VIDEO_TO
        write_status(job_dir, 100, "DONE", "Video ready")
        tracker.complete(final_video if final_video and os.path.exists(final_video) else None)

        # Return a dict similar to your original CLI return
        return {
            "script": formatted_script,
            "audio_path": audio_path,
            "image_paths": image_paths,
            "video_path": final_video if final_video and os.path.exists(final_video) else None,
            "job_dir": job_dir
        }

    except Exception as e:
        logger.error(f"Error in main process: {str(e)}")
        logger.error(traceback.format_exc())
        write_status(job_dir, 0, "ERROR", str(e))
        if 'tracker' in locals():
            tracker.error("Fatal error in generation process", e)
        # propagate exception so a Celery task or FastAPI can detect failure
        raise

# --------------------------
# CLI compatibility: keep the original main() behavior
# --------------------------
def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Text-to-Video Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--topic", "-t",
        type=str,
        help="Topic for video generation"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output_video.mp4",
        help="Output filename for the generated video"
    )

    parser.add_argument(
        "--no-captions",
        action="store_true",
        help="Skip caption generation"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip cleanup of temporary files"
    )

    return parser.parse_args()

def main_cli():
    args = parse_arguments()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    topic = args.topic
    if not topic:
        topic = input("Enter a topic for your video: ")

    job_id = f"local-{int(time.time())}"
    outputs_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "outputs"))
    os.makedirs(outputs_root, exist_ok=True)

    try:
        result = generate_video_from_prompt(topic, job_id, outputs_root=outputs_root, skip_cleanup=args.skip_cleanup, no_captions=args.no_captions, debug=args.debug)
        video_path = result.get("video_path")
        if args.output and video_path:
            try:
                out_path = os.path.join(os.path.dirname(video_path), args.output)
                os.replace(video_path, out_path)
                print("Video saved to:", out_path)
            except Exception:
                print("Video generated at:", video_path)
        else:
            print("Video generated at:", video_path or "No video path produced")
    except Exception as e:
        print("Generation failed:", str(e))
        logger.exception("Generation failed")

if __name__ == "__main__":
    main_cli()
