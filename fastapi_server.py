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
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",    
        "service": "Phone Detective Analysis",
        "version": "1.0.0"
    }

@app.post('/analyze-async', response_model=AsyncAnalysisResponse)
async def run_analysis_async(request: AnalysisRequest, background_tasks:BackgroundTasks) -> AsyncAnalysisResponse:
    try:
        task_id = str(uuid.uuid4())
        with task_lock:
            task_store[task_id] = {
                "task_id": task_id,
                "status": "pending",
                "progress": "Task queued for processing",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "folder_path": request.folder_path,
                "target_language": request.target_language,
                "similarity_threshold": request.similarity_threshold,
                "result": None,
                "error": None
            }
        background_tasks.add_task(
            run_analysis_background,
            task_id,
            request.folder_path,
            request.target_language,
            request.similarity_threshold
        )
        logger.info(f'Started async analysis task {task_id} for folder: {request.folder_path}')
        return AsyncAnalysisResponse(
            task_id= task_id,
            status= "pending",
            message= f'Analysis task started. Use /status/{task_id} to check progress.',
            estimated_time_minutes=10 
        )
    except Exception as e:
        logger.error(f'Failed to start async anaalysis: {e}')
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")

@app.post("/analyze", response_model=AnalysisResponse)
async def run_analysis(request: AnalysisRequest) -> AnalysisResponse:
    try:
        logger.info(f'Starting analysis for folder: {request.folder_path}')
        logger.info(f'Target language: {request.target_language}')
        logger.info(f'Similarity threshold: {request.similarity_threshold}')
        report_file_path = run_analysis_and_generate_report(
            folder_path=request.folder_path,
            target_language=request.target_language,
            similarity_threshold=request.similarity_threshold
        )
        report_data = None

        你好
         
