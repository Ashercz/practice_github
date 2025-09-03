from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, validator, field_validator
from pathlib import Path
import json
import logging
import uuid
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pymongo.errors import ConnectionFailure, ConfigurationError
from pd_workflow import run_analysis_and_generate_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

task_store = {}
task_lock = threading.Lock()

app = FastAPI(
    title= "Phone Detective Analysis API",
    description= "Internal API fo running UI analysis workflow on Android screenshots",
    version="1.0.0"
)

class AnalysisRequest(BaseModel):
    folder_path: str
    target_language: str = "en"
    similarity_threshold: float = 0.9
    
    @field_validator('folder_path')
    def validate_folder_path(cls, v):
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Folder path doesn't exist {v}")
        if not path.is_dir():
            raise ValueError(f"Path is not a directory")
        return str(path.resolve())
    
    @field_validator("target_language")
    def validate_target_language(cls, v):
        if not v or not isinstance(v, str):
            raise ValueError(f"Target language must be a non-empty string")
        return v.strip()
    
    @field_validator("similarity_threshold")
    def validate_similarity_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Similarity threshold must be between 0.0 and 1.0")
        return v
    
class AnalysisResponse(BaseModel):
    success: bool
    report_file_path: str = None
    report_data: Dict[Any, Any] = None
    error: str = None
    message: str = None

class AsyncAnalysisResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_time_minutes: int = 10

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[str] = None
    created_at: str
    updated_at: str
    result: Optional[Dict[Any, Any]] = None
    error: Optional[str] = None

asdad

asdad