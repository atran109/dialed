"""
FastAPI backend for Dialed study-session distraction classifier.

Endpoints:
- POST /log/tab: Log browser tab activity
- POST /log/gaze: Log gaze tracking data
- POST /log/label: Log user focus labels
- POST /predict: Get distraction prediction (future)
- GET /health: Health check
- GET /stats: Get database statistics
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import (
    init_db,
    insert_gaze_log,
    insert_tab_log,
    insert_label,
    get_stats,
    get_gaze_logs,
    get_tab_logs,
    get_labels
)

# Initialize FastAPI app
app = FastAPI(
    title="Dialed API",
    description="Backend for study-session distraction classifier",
    version="1.0.0"
)

# Enable CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class TabLog(BaseModel):
    """Browser tab activity log."""
    timestamp: float = Field(..., description="Unix timestamp in seconds")
    domain: str = Field(..., description="Domain of active tab")
    title: str = Field(..., description="Title of active tab")
    idle_state: str = Field(..., description="Idle state: active, idle, or locked")
    keypress_count: int = Field(0, description="Number of keypresses in interval")


class GazeLog(BaseModel):
    """Gaze tracking log from webcam."""
    timestamp: float
    eye_off_center: float = Field(..., ge=0.0, le=1.0)
    blink: int = Field(..., ge=0, le=1)
    head_pitch: float
    head_yaw: float
    head_distance: float = Field(..., ge=0.0, le=1.0)


class Label(BaseModel):
    """User-provided focus label."""
    timestamp: float
    label: str = Field(..., pattern="^(distracted|focused)$")


class PredictionRequest(BaseModel):
    """Request for distraction prediction."""
    features: dict  # Will be defined later when we build feature pipeline


class PredictionResponse(BaseModel):
    """Response with distraction probability."""
    prob_distracted: float = Field(..., ge=0.0, le=1.0)
    prob_focused: float = Field(..., ge=0.0, le=1.0)
    prediction: str


class StatsResponse(BaseModel):
    """Database statistics."""
    gaze_logs: int
    tab_logs: int
    labels: int
    label_breakdown: dict


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database when server starts."""
    init_db()
    print("Database initialized")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Check if server is running."""
    return {"status": "healthy", "timestamp": time.time()}


# Statistics endpoint
@app.get("/stats", response_model=StatsResponse)
async def get_statistics():
    """Get database statistics."""
    stats = get_stats()
    return stats


# Logging endpoints
@app.post("/log/tab")
async def log_tab(tab_log: TabLog):
    """Log browser tab activity."""
    try:
        insert_tab_log(
            timestamp=tab_log.timestamp,
            domain=tab_log.domain,
            title=tab_log.title,
            idle_state=tab_log.idle_state,
            keypress_count=tab_log.keypress_count
        )
        return {"status": "success", "message": "Tab log saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/log/gaze")
async def log_gaze(gaze_log: GazeLog):
    """Log gaze tracking data."""
    try:
        insert_gaze_log(
            timestamp=gaze_log.timestamp,
            eye_off_center=gaze_log.eye_off_center,
            blink=gaze_log.blink,
            head_pitch=gaze_log.head_pitch,
            head_yaw=gaze_log.head_yaw,
            head_distance=gaze_log.head_distance
        )
        return {"status": "success", "message": "Gaze log saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/log/label")
async def log_label(label: Label):
    """Log user-provided focus label."""
    try:
        insert_label(
            timestamp=label.timestamp,
            label=label.label
        )
        return {"status": "success", "message": f"Label '{label.label}' saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Data retrieval endpoints
@app.get("/data/gaze")
async def get_gaze_data(start_time: Optional[float] = None, end_time: Optional[float] = None):
    """Get gaze logs within time range."""
    try:
        logs = get_gaze_logs(start_time, end_time)
        return {"count": len(logs), "data": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/tabs")
async def get_tab_data(start_time: Optional[float] = None, end_time: Optional[float] = None):
    """Get tab logs within time range."""
    try:
        logs = get_tab_logs(start_time, end_time)
        return {"count": len(logs), "data": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data/labels")
async def get_label_data(start_time: Optional[float] = None, end_time: Optional[float] = None):
    """Get labels within time range."""
    try:
        logs = get_labels(start_time, end_time)
        return {"count": len(logs), "data": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Prediction endpoint (placeholder for future)
@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Predict distraction probability from features.
    TODO: Implement this after model training phase.
    """
    # Placeholder response
    return {
        "prob_distracted": 0.5,
        "prob_focused": 0.5,
        "prediction": "unknown"
    }


def main():
    """Run the FastAPI server."""
    print("Starting Dialed backend server...")
    print("Server will be available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
