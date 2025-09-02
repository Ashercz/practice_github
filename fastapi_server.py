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

def update_task_status(task_id: str, status: str, progress: str = None, result: Dict[Any, Any] = None, error: str =None):
    with task_lock:
        if task_id in task_store:
            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat()
            }
            if progress is not None:
                update_data['progress'] = progress
            if result is not None:
                update_data['result'] = result
            if error is not None:
                update_data['error'] = error
            task_store[task_id].update(update_data)
            logger.info(f"Updated task {task_id}")
        else:
            logger.error(f"Attempted to update non-existent task: {task_id}")
def run_analysis_background(task_id: str, folder_path: str, target_language: str, similarity_threshold: float):
    try:
        logger.info(f"Starting background analysis for tast {task_id}")
        update_task_status(task_id, 'running', 'Starting analysis workflow...')
        update_task_status(task_id, 'running', 'Converting XML files and detecting duplicates...')
        report_file_path = run_analysis_and_generate_report(
            folder_path=folder_path,
            target_language=target_language,
            similarity_threshold=similarity_threshold,
        )
        logger.info(f"report地址：{report_file_path}.\n")
        report_data = None
        if report_file_path and Path(report_file_path).exists():
            try:
                update_task_status(task_id, "running", "Loading report data...")
                with open(report_file_path, 'r', encoding='utf-8') as f:
                    report_data =json.load(f)
                logger.info(f'Successfully loaded report data from:{report_file_path} ')
            except Exception as e:
                logger.warning(f'Could not read report file {report_file_path}: {e}')
        result = {
            "success": True,
            "report_file_path": report_file_path,
            "report_data": report_data,
            "message": f"Analysis completed successfully. Report asved to: {report_file_path}"
        }
        update_task_status(task_id, "completed", "Analysis completed successfully!", result)
        logger.info(f'Background analysis completed for task {task_id}')
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        logger.error(f'Background analysis failed for task {task_id}: {e}')
        update_task_status(task_id, "failed", error=error_msg)

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
         