# backend/app.py
import uuid
import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from pipeline.main import generate_video_from_prompt

app = FastAPI(title="Text-to-Video API")

# Allow frontend (React/Next.js/Vue etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- change to your domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_ROOT = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUTS_ROOT, exist_ok=True)


# --------------------------------------------------
#  POST /generate
# --------------------------------------------------
@app.post("/generate")
async def generate_video(prompt: str, background_tasks: BackgroundTasks):
    """
    Receives a text prompt from frontend.
    Starts video generation in background.
    Returns a job_id for polling.
    """
    if not prompt or len(prompt.strip()) == 0:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(OUTPUTS_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    # Start background video generation (non-blocking)
    background_tasks.add_task(
        generate_video_from_prompt,
        prompt,
        job_id,
        OUTPUTS_ROOT,
        False,   # skip_cleanup
        False,   # no_captions
        False    # debug
    )

    return {"job_id": job_id, "status": "started"}


# --------------------------------------------------
#  GET /status/{job_id}
# --------------------------------------------------
@app.get("/status/{job_id}")
async def check_status(job_id: str):
    """
    Returns the progress and messages of the running job.
    Frontend should poll this endpoint.
    """
    job_dir = os.path.join(OUTPUTS_ROOT, job_id)
    status_file = os.path.join(job_dir, "status.json")

    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Invalid job_id")

    if not os.path.exists(status_file):
        return {"progress": 0, "stage": "QUEUED", "message": "Waiting to start..."}

    import json
    with open(status_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # If video is ready, include video URL
    video_path = os.path.join(job_dir, "Video", "Video.mp4")
    if os.path.exists(video_path):
        data["video_ready"] = True
        data["video_url"] = f"/download/{job_id}"

    return data


# --------------------------------------------------
#  GET /download/{job_id}
# --------------------------------------------------
@app.get("/download/{job_id}")
async def download_video(job_id: str):
    """
    Returns the generated final video file.
    """
    video_path = os.path.join(OUTPUTS_ROOT, job_id, "Video", "Video.mp4")

    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not ready yet")

    return FileResponse(video_path, media_type="video/mp4", filename="video.mp4")
