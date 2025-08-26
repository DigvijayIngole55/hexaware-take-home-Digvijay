from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import json
import os
from datetime import datetime
from google_drive_utils import download_all_files_from_folder
from pdf_utils import extract_text_from_files_list

DEBUG = True
DEBUG_DOWNLOAD_FILE = "download_result.json"
DEBUG_EXTRACTION_FILE = "extraction_result.json"

def save_download_result(result: dict, url: str):
    if not DEBUG:
        return
    
    debug_data = {
        "timestamp": datetime.now().isoformat(),
        "url": url,
        "result": result
    }
    
    try:
        with open(DEBUG_DOWNLOAD_FILE, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        pass

def load_download_result() -> dict:
    if not DEBUG or not os.path.exists(DEBUG_DOWNLOAD_FILE):
        return None
    
    try:
        with open(DEBUG_DOWNLOAD_FILE, 'r', encoding='utf-8') as f:
            debug_data = json.load(f)
            return debug_data.get("result")
    except Exception as e:
        return None

def save_extraction_result(extraction_results: list, url: str):
    if not DEBUG:
        return
    
    debug_data = {
        "timestamp": datetime.now().isoformat(),
        "url": url,
        "extraction_results": extraction_results
    }
    
    try:
        with open(DEBUG_EXTRACTION_FILE, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        pass

def load_extraction_result() -> list:
    if not DEBUG or not os.path.exists(DEBUG_EXTRACTION_FILE):
        return None
    
    try:
        with open(DEBUG_EXTRACTION_FILE, 'r', encoding='utf-8') as f:
            debug_data = json.load(f)
            return debug_data.get("extraction_results")
    except Exception as e:
        return None

app = FastAPI(title="RAG Pipeline API", description="A RAG injection pipeline from Google Drive", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    
class QueryResponse(BaseModel):
    answer: str
    citations: List[str]
    
class IngestRequest(BaseModel):
    google_drive_url: str
    
class FileInfo(BaseModel):
    id: str
    name: str
    download_link: str
    local_path: str

class PageInfo(BaseModel):
    page: int
    text: str
    char_count: int
    ocr_used: Optional[bool] = False
    original_char_count: Optional[int] = None
    ocr_error: Optional[str] = None

class ExtractedFileInfo(BaseModel):
    file_id: str
    filename: str
    filepath: str
    download_link: str
    success: bool
    text: str
    page_count: int
    char_count: int
    word_count: int
    pages: List[PageInfo]
    metadata: dict
    ocr_pages_count: Optional[int] = 0
    error: Optional[str]

class IngestResponse(BaseModel):
    status: str
    message: str
    documents_processed: int
    files: List[FileInfo]
    extracted_texts: List[ExtractedFileInfo]

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    return QueryResponse(
        answer="This is a placeholder answer for: " + request.question,
        citations=["Document 1", "Document 2"]
    )



@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    if DEBUG:
        cached_download = load_download_result()
        if cached_download:
            result = cached_download
        else:
            result = download_all_files_from_folder(request.google_drive_url)
            save_download_result(result, request.google_drive_url)
    else:
        result = download_all_files_from_folder(request.google_drive_url)
    
    if not result["success"] or not result.get("files"):
        return IngestResponse(
            status="error",
            message=result["message"],
            documents_processed=result["count"],
            files=result.get("files", []),
            extracted_texts=[]
        )
    
    if DEBUG:
        cached_extraction = load_extraction_result()
        if cached_extraction:
            extraction_results = cached_extraction
        else:
            extraction_results = extract_text_from_files_list(result["files"])
            save_extraction_result(extraction_results, request.google_drive_url)
    else:
        extraction_results = extract_text_from_files_list(result["files"])
    
    successful_extractions = [r for r in extraction_results if r["success"]]
    extraction_message = f"Downloaded {result['count']} files, extracted text from {len(successful_extractions)}"
    
    return IngestResponse(
        status="success" if result["success"] and successful_extractions else "partial" if result["success"] else "error",
        message=extraction_message,
        documents_processed=result["count"],
        files=result.get("files", []),
        extracted_texts=extraction_results
    )



@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now()
    )

@app.get("/")
async def root():
    return {
        "message": "RAG Pipeline API",
        "version": "1.0.0",
        "endpoints": {
            "POST /query": "Submit a question and get an answer with citations",
            "POST /ingest": "Download documents from Google Drive and extract text",
            "GET /healthz": "Health check"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)