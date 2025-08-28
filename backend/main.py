from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import uvicorn
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
from google_drive_utils import download_all_files_from_folder
from pdf_utils import extract_text_from_files_list
from corpus_utils import create_corpus_from_extraction, save_corpus_result, load_corpus_result
from chunking_utils import create_chunks_from_corpus, add_dense_vectors, create_elasticsearch_documents, save_chunks_result, load_chunks_result
from sentence_transformers import SentenceTransformer
from elasticsearch_utils import get_elasticsearch_client, create_chunks_index, index_chunks, get_index_stats, search_bm25, search_dense_vector, search_elser, search_hybrid, search_hybrid_rrf
from ollama_utils import generate_answer_from_chunks

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    type: Optional[str] = "hybrid"
    size: Optional[int] = 5
    k: Optional[int] = 60
    use_llm: Optional[bool] = True
    
class QueryResponse(BaseModel):
    answer: str
    citations: List[str]
    sources_used: Optional[int] = 0
    source_files: Optional[List[str]] = []
    generation_method: Optional[str] = "retrieval_only"
    
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
    print(f"Processing query: '{request.question}' with type: {request.type}, use_llm: {request.use_llm}")
    
    try:
        if request.type == "hybrid":
            query_vector = generate_query_embedding(request.question)
            if not query_vector:
                print("Warning: Failed to generate query embedding, proceeding without dense vector")
            
            result = search_hybrid_rrf(
                query=request.question,
                query_vector=query_vector,
                size=request.size,
                k=request.k
            )
            
            print(f"\n HYBRID RRF SEARCH RESULTS ({len(result['results'])} found):")
            if result["success"] and result["results"]:
                for i, hit in enumerate(result["results"], 1):
                    rrf_score = hit.get('rrf_score', 0)
                    found_in = hit.get('found_in', {})
                    methods = [k for k, v in found_in.items() if v]
                    print(f"{i}. [{hit['filename']}] RRF Score: {rrf_score:.4f}")
                    print(f"   Found in: {', '.join(methods)}")
                    print(f"   Text: {hit['raw_text'][:150]}...")
                    print()
                        
        elif request.type == "elser":
            result = search_elser(
                query=request.question,
                size=request.size,
                min_score=0.0
            )
            
            print(f"\n ELSER SEARCH RESULTS ({len(result['results'])} found):")
            if result["success"] and result["results"]:
                for i, hit in enumerate(result["results"], 1):
                    print(f"{i}. [{hit['filename']}] Score: {hit['score']:.3f}")
                    print(f"   Text: {hit['raw_text'][:150]}...")
                    print()
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid search type: {request.type}. Supported types: hybrid, elser"
            )
        
        if not result["success"]:
            return QueryResponse(
                answer=f"Search failed: {result.get('error', 'Unknown error')}",
                citations=[],
                generation_method="error"
            )
        
        if request.use_llm and result["results"]:
            print(f"\n🤖 GENERATING LLM ANSWER using {len(result['results'])} retrieved chunks...")
            
            llm_result = generate_answer_from_chunks(
                query=request.question,
                chunks=result["results"],
                max_chunks=min(request.size, 5),
                model_name="gemma3:4b"
            )
            
            if llm_result["success"]:
                answer = llm_result["answer"]
                generation_method = "llm_generated"
                sources_used = llm_result.get("sources_used", 0)
                source_files = llm_result.get("source_files", [])
                
                citations = [f"{filename}" for filename in source_files[:5]]
                
                print(f"✅ LLM successfully generated answer using {sources_used} sources")
            else:
                print(f"❌ LLM generation failed: {llm_result.get('error')}")
                answer = f"I found {len(result['results'])} relevant documents but couldn't generate a comprehensive answer. Please try again or check if the Hugging Face API is available."
                generation_method = "llm_failed"
                sources_used = 0
                source_files = []
                citations = [f"{r['filename']}" for r in result["results"][:3]]
        else:
            if request.type == "hybrid":
                answer = f"Found {len(result['results'])} relevant documents:\n\n"
                for i, hit in enumerate(result["results"][:3], 1):
                    answer += f"{i}. **{hit['filename']}**\n"
                    answer += f"   {hit['raw_text'][:200]}...\n\n"
            else:
                answer = f"Found {len(result['results'])} relevant documents using ELSER search.\n\n"
                for i, hit in enumerate(result["results"][:3], 1):
                    answer += f"{i}. **{hit['filename']}** (Score: {hit['score']:.3f})\n"
                    answer += f"   {hit['raw_text'][:200]}...\n\n"
            
            generation_method = "retrieval_only"
            sources_used = len(result["results"])
            source_files = [r['filename'] for r in result["results"]]
            citations = [f"{r['filename']}" for r in result["results"][:5]]
        
        return QueryResponse(
            answer=answer,
            citations=citations,
            sources_used=sources_used,
            source_files=source_files,
            generation_method=generation_method
        )
        
    except Exception as e:
        print(f"Error processing query: {e}")
        return QueryResponse(
            answer=f"Error processing query: {str(e)}",
            citations=[],
            generation_method="error"
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