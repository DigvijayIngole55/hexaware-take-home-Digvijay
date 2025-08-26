from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import json
import os
from datetime import datetime
from google_drive_utils import download_all_files_from_folder
from pdf_utils import extract_text_from_files_list
from corpus_utils import create_corpus_from_extraction, save_corpus_result, load_corpus_result
from chunking_utils import create_chunks_from_corpus, add_dense_vectors, create_elasticsearch_documents, save_chunks_result, load_chunks_result
from sentence_transformers import SentenceTransformer
from elasticsearch_utils import get_elasticsearch_client, create_chunks_index, index_chunks, get_index_stats, search_bm25, search_dense_vector, search_elser, search_hybrid

DEBUG = True
AUTO_LOAD_TO_ELASTICSEARCH = True  
DEBUG_DOWNLOAD_FILE = "cache/download_result.json"
DEBUG_EXTRACTION_FILE = "cache/extraction_result.json"
DEBUG_CORPUS_FILE = "cache/corpus_result.json"
DEBUG_CHUNKS_FILE = "cache/chunks_result.json"

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print("Loading embedding model: sentence-transformers/all-MiniLM-L6-v2")
        _embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _embedding_model

def generate_query_embedding(query: str) -> List[float]:
    try:
        model = get_embedding_model()
        embedding = model.encode(query)
        return embedding.tolist()
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def ensure_cache_directory():
    cache_dir = "cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

def save_download_result(result: dict, url: str):
    if not DEBUG:
        return
    
    ensure_cache_directory()
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
    
    ensure_cache_directory()
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
    search_type: Optional[str] = "hybrid"
    size: Optional[int] = 10
    min_score: Optional[float] = 0.1
    
class QueryResponse(BaseModel):
    answer: str
    citations: List[str]

class SearchRequest(BaseModel):
    query: str
    search_type: str = "bm25"
    size: Optional[int] = 10
    min_score: Optional[float] = 0.1
    bm25_weight: Optional[float] = 0.2
    dense_weight: Optional[float] = 0.3
    elser_weight: Optional[float] = 0.5

class SearchResult(BaseModel):
    chunk_id: str
    filename: str
    drive_url: str
    raw_text: str
    score: float
    metadata: Dict
    highlights: Optional[Dict] = None

class SearchResponse(BaseModel):
    success: bool
    search_type: str
    query: str
    total_hits: int
    max_score: Optional[float]
    results: List[SearchResult]
    took_ms: int
    error: Optional[str] = None
    weights: Optional[Dict] = None
    
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

class CorpusItem(BaseModel):
    pdf_name: str
    pdf_link: str
    corpus: str

class ChunkDocument(BaseModel):
    chunk_id: str
    filename: str
    drive_url: str
    raw_text: str
    dense_vector: List[float]
    text_for_elser: str
    metadata: Dict

class IngestResponse(BaseModel):
    status: str
    message: str
    documents_processed: int
    files: List[FileInfo]
    extracted_texts: List[ExtractedFileInfo]
    corpus: List[CorpusItem]
    chunks: List[ChunkDocument]
    chunks_count: int
    elasticsearch_indexed: int
    elasticsearch_status: str

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    print(f"Processing query: '{request.question}' with all search types")
    
    try:
        query_vector = generate_query_embedding(request.question)
        
        print("Calling BM25 search...")
        bm25_result = search_bm25(
            query=request.question,
            size=5,
            min_score=0.1
        )
        
        print("Calling Dense Vector search...")
        dense_result = None
        if query_vector:
            print(f"Generated embedding vector length: {len(query_vector)}")
            print(f"First 5 values: {query_vector[:5]}")
            dense_result = search_dense_vector(
                query_vector=query_vector,
                size=5
            )
        
        print("Calling ELSER search...")
        elser_result = search_elser(
            query=request.question,
            size=5,
            min_score=0.1
        )
        
        print("\n" + "="*80)
        print(f"SEARCH RESULTS COMPARISON FOR: '{request.question}'")
        print("="*80)
        
        print("\n🔍 BM25 SEARCH RESULTS:")
        if bm25_result["success"] and bm25_result["results"]:
            for i, result in enumerate(bm25_result["results"], 1):
                print(f"{i}. [{result['filename']}] Score: {result['score']:.3f}")
                print(f"   Text: {result['raw_text'][:150]}...")
                print()
        else:
            print("   No BM25 results found")
        
        print("\n🧠 DENSE VECTOR SEARCH RESULTS:")
        if dense_result and dense_result["success"] and dense_result["results"]:
            for i, result in enumerate(dense_result["results"], 1):
                print(f"{i}. [{result['filename']}] Score: {result['score']:.3f}")
                print(f"   Text: {result['raw_text'][:150]}...")
                print()
        else:
            print("   No Dense Vector results found")
        
        print("\n🎯 ELSER SEARCH RESULTS:")
        if elser_result["success"] and elser_result["results"]:
            for i, result in enumerate(elser_result["results"], 1):
                print(f"{i}. [{result['filename']}] Score: {result['score']:.3f}")
                print(f"   Text: {result['raw_text'][:150]}...")
                print()
        else:
            print("   No ELSER results found")
        
        print("="*80)
        bm25_count = len(bm25_result["results"]) if bm25_result["success"] else 0
        dense_count = len(dense_result["results"]) if dense_result and dense_result["success"] else 0
        elser_count = len(elser_result["results"]) if elser_result["success"] else 0
        
        answer = f"Search comparison for '{request.question}':\n"
        answer += f"• BM25: {bm25_count} results\n"
        answer += f"• Dense Vector: {dense_count} results\n"
        answer += f"• ELSER: {elser_count} results\n\n"
        answer += "Check the console output for detailed results comparison."
        citations = []
        if bm25_result["success"]:
            citations.extend([f"BM25: {r['filename']} ({r['score']:.3f})" for r in bm25_result["results"][:2]])
        if dense_result and dense_result["success"]:
            citations.extend([f"Dense: {r['filename']} ({r['score']:.3f})" for r in dense_result["results"][:2]])
        if elser_result["success"]:
            citations.extend([f"ELSER: {r['filename']} ({r['score']:.3f})" for r in elser_result["results"][:2]])
        
        return QueryResponse(
            answer=answer,
            citations=citations[:6]
        )
        
    except Exception as e:
        print(f"Error processing query: {e}")
        return QueryResponse(
            answer=f"Error processing query: {str(e)}",
            citations=[]
        )



@app.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    print(f"Starting ingest process for URL: {request.google_drive_url}")
    print(f"DEBUG mode: {DEBUG}, AUTO_LOAD_TO_ELASTICSEARCH: {AUTO_LOAD_TO_ELASTICSEARCH}")
    if DEBUG:
        print("Checking for cached download result...")
        cached_download = load_download_result()
        if cached_download:
            print("Using cached download result")
            result = cached_download
        else:
            print("No cached download found, downloading from Google Drive...")
            result = download_all_files_from_folder(request.google_drive_url)
            save_download_result(result, request.google_drive_url)
    else:
        print("Downloading from Google Drive (DEBUG=False)...")
        result = download_all_files_from_folder(request.google_drive_url)
    
    if not result["success"] or not result.get("files"):
        print(f"Download failed: {result['message']}")
        return IngestResponse(
            status="error",
            message=result["message"],
            documents_processed=result["count"],
            files=result.get("files", []),
            extracted_texts=[],
            corpus=[],
            chunks=[],
            chunks_count=0,
            elasticsearch_indexed=0,
            elasticsearch_status="not attempted"
        )
    
    print(f"Processing {result['count']} downloaded files...")
    if DEBUG:
        print("Checking for cached extraction result...")
        cached_extraction = load_extraction_result()
        if cached_extraction:
            print("Using cached extraction result")
            extraction_results = cached_extraction
        else:
            print("No cached extraction found, extracting text...")
            extraction_results = extract_text_from_files_list(result["files"])
            save_extraction_result(extraction_results, request.google_drive_url)
    else:
        print("Extracting text from files (DEBUG=False)...")
        extraction_results = extract_text_from_files_list(result["files"])
    
    if DEBUG:
        print("Checking for cached corpus result...")
        cached_corpus = load_corpus_result(DEBUG_CORPUS_FILE)
        if cached_corpus:
            print(f"Using cached corpus with {len(cached_corpus)} documents")
            corpus = cached_corpus
        else:
            print("No cached corpus found, creating corpus...")
            corpus = create_corpus_from_extraction(extraction_results)
            save_corpus_result(corpus, request.google_drive_url, DEBUG_CORPUS_FILE)
    else:
        print("Creating corpus (DEBUG=False)...")
        corpus = create_corpus_from_extraction(extraction_results)
    
    if DEBUG:
        print("Checking for cached chunks result...")
        cached_chunks = load_chunks_result(DEBUG_CHUNKS_FILE)
        if cached_chunks:
            print(f"Using cached chunks: {len(cached_chunks)} chunks loaded")
            chunks = cached_chunks
        else:
            print("No cached chunks found, creating chunks...")
            chunks = create_chunks_from_corpus(corpus)
            print(f"Created {len(chunks)} text chunks")
            print("Adding dense vectors to chunks...")
            chunks = add_dense_vectors(chunks)
            print("Creating Elasticsearch documents...")
            chunks = create_elasticsearch_documents(chunks)
            save_chunks_result(chunks, request.google_drive_url, DEBUG_CHUNKS_FILE)
    else:
        print("Creating chunks (DEBUG=False)...")
        chunks = create_chunks_from_corpus(corpus)
        print(f"Created {len(chunks)} text chunks")
        print("Adding dense vectors to chunks...")
        chunks = add_dense_vectors(chunks)
        print("Creating Elasticsearch documents...")
        chunks = create_elasticsearch_documents(chunks)
    
    elasticsearch_result = {"success": False, "message": "Elasticsearch loading disabled", "indexed_count": 0}
    
    if AUTO_LOAD_TO_ELASTICSEARCH and chunks:
        print(f"Starting Elasticsearch indexing for {len(chunks)} chunks...")
        try:
            create_chunks_index("hexaware_chunks")
            elasticsearch_result = index_chunks(chunks, "hexaware_chunks")
            print(f"Elasticsearch indexing completed: {elasticsearch_result['message']}")
        except Exception as e:
            print(f"Elasticsearch indexing failed: {str(e)}")
            elasticsearch_result = {"success": False, "message": f"Elasticsearch error: {str(e)}", "indexed_count": 0}
    elif not AUTO_LOAD_TO_ELASTICSEARCH:
        print("Elasticsearch indexing skipped (AUTO_LOAD_TO_ELASTICSEARCH=False)")
    elif not chunks:
        print("Elasticsearch indexing skipped (no chunks available)")
    
    successful_extractions = [r for r in extraction_results if r["success"]]
    es_message = f", indexed {elasticsearch_result['indexed_count']} chunks to Elasticsearch" if elasticsearch_result["success"] else ""
    extraction_message = f"Downloaded {result['count']} files, extracted text from {len(successful_extractions)}, created corpus for {len(corpus)} documents, generated {len(chunks)} chunks{es_message}"
    
    print(f"Ingest process completed: {extraction_message}")
    
    response_status = "success" if result["success"] and successful_extractions else "partial" if result["success"] else "error"
    print(f"Returning response with status: {response_status}")
    
    return IngestResponse(
        status=response_status,
        message=extraction_message,
        documents_processed=result["count"],
        files=result.get("files", []),
        extracted_texts=extraction_results,
        corpus=corpus,
        chunks=chunks,
        chunks_count=len(chunks),
        elasticsearch_indexed=elasticsearch_result["indexed_count"],
        elasticsearch_status="success" if elasticsearch_result["success"] else elasticsearch_result["message"]
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
            "POST /ingest": "Download documents, extract text, create chunks, and index to Elasticsearch",
            "GET /healthz": "Health check"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)