# backend/app.py
from dotenv import load_dotenv
import os
import json

load_dotenv()  # <-- THIS IS THE FIX

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import os

from pipeline.main import generate_video_from_prompt

app = FastAPI(title="Text to Video API")

# CORS middleware - allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUTS_ROOT = os.path.join(os.path.dirname(__file__), "outputs")

# Mount outputs folder to serve video files
if os.path.exists(OUTPUTS_ROOT):
    app.mount("/outputs", StaticFiles(directory=OUTPUTS_ROOT), name="outputs")

class VideoRequest(BaseModel):
    prompt: str

@app.get("/")
def health_check():
    return {"status": "Backend is running 🚀"}

@app.post("/generate")
def generate_video(request: VideoRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())

    background_tasks.add_task(
        generate_video_from_prompt,
        prompt=request.prompt,
        job_id=job_id,
        outputs_root=OUTPUTS_ROOT
    )

    return {
        "message": "Video generation started",
        "job_id": job_id
    }

@app.get("/status/{job_id}")
def get_status(job_id: str):
    status_file = os.path.join(OUTPUTS_ROOT, job_id, "status.json")

    if not os.path.exists(status_file):
        return {"state": "not_found", "progress": 0, "message": "Job not found"}

    with open(status_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Map backend stage to frontend-expected state
    stage = data.get("stage", "")
    progress = data.get("progress", 0)
    message = data.get("message", "")
    
    # Map stage to state for frontend compatibility
    if stage == "DONE":
        state = "completed"
        video_url = f"http://127.0.0.1:8000/outputs/{job_id}/Video/Video.mp4"
    elif stage == "ERROR":
        state = "failed"
        video_url = None
    else:
        state = "processing"
        video_url = None
    
    return {
        "state": state,
        "stage": stage,
        "progress": progress,
        "message": message,
        "video_url": video_url
    }

@app.get("/video/{job_id}")
def get_video(job_id: str):
    """Serve the generated video file"""
    video_path = os.path.join(OUTPUTS_ROOT, job_id, "Video", "Video.mp4")
    
    if not os.path.exists(video_path):
        return {"error": "Video not found"}
    
    return FileResponse(video_path, media_type="video/mp4", filename=f"{job_id}.mp4")
