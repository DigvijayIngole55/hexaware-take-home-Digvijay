import os
import json
import tiktoken
from typing import List, Dict
from datetime import datetime
from sentence_transformers import SentenceTransformer


def chunk_text_by_tokens(text: str, max_tokens: int = 300, overlap_tokens: int = 50) -> List[str]:
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
        
        if end >= len(tokens):
            break
            
        start = end - overlap_tokens
    
    return chunks


def create_chunks_from_corpus(corpus: List[Dict[str, str]]) -> List[Dict]:
    all_chunks = []
    
    for corpus_item in corpus:
        pdf_name = corpus_item.get("pdf_name", "")
        pdf_link = corpus_item.get("pdf_link", "")
        text = corpus_item.get("corpus", "")
        
        if not text.strip():
            continue
            
        text_chunks = chunk_text_by_tokens(text)
        
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{pdf_name.replace('.pdf', '').replace(' ', '_').lower()}_chunk_{i+1:03d}"
            
            chunk_doc = {
                "chunk_id": chunk_id,
                "filename": pdf_name,
                "drive_url": pdf_link,
                "raw_text": chunk_text.strip(),
                "text_for_elser": chunk_text.strip(),
                "chunk_index": i + 1,
                "total_chunks": len(text_chunks),
                "token_count": len(tiktoken.get_encoding("cl100k_base").encode(chunk_text))
            }
            
            all_chunks.append(chunk_doc)
    
    return all_chunks


def add_dense_vectors(chunks: List[Dict]) -> List[Dict]:
    if not chunks:
        return chunks
    
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    texts = [chunk["raw_text"] for chunk in chunks]
    vectors = model.encode(texts, convert_to_tensor=False)
    
    for i, chunk in enumerate(chunks):
        chunk["dense_vector"] = vectors[i].tolist()
    
    return chunks


def create_elasticsearch_documents(chunks: List[Dict]) -> List[Dict]:
    elasticsearch_docs = []
    
    for chunk in chunks:
        es_doc = {
            "chunk_id": chunk["chunk_id"],
            "filename": chunk["filename"],
            "drive_url": chunk["drive_url"],
            "raw_text": chunk["raw_text"],
            "dense_vector": chunk["dense_vector"],
            "text_for_elser": chunk["text_for_elser"],
            "metadata": {
                "filename": chunk["filename"],
                "drive_url": chunk["drive_url"],
                "chunk_id": chunk["chunk_id"],
                "chunk_index": chunk["chunk_index"],
                "total_chunks": chunk["total_chunks"],
                "token_count": chunk["token_count"]
            }
        }
        
        elasticsearch_docs.append(es_doc)
    
    return elasticsearch_docs


def save_chunks_result(chunks: List[Dict], url: str, debug_file: str = "cache/chunks_result.json"):
    try:
        cache_dir = os.path.dirname(debug_file)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "chunks_count": len(chunks),
            "total_documents": len(set(chunk["filename"] for chunk in chunks)),
            "chunks": chunks
        }
        
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        pass


def load_chunks_result(debug_file: str = "cache/chunks_result.json") -> List[Dict]:
    if not os.path.exists(debug_file):
        return None
    
    try:
        with open(debug_file, 'r', encoding='utf-8') as f:
            debug_data = json.load(f)
            return debug_data.get("chunks")
    except Exception as e:
        return None


def get_chunks_statistics(chunks: List[Dict]) -> Dict[str, any]:
    if not chunks:
        return {
            "total_chunks": 0,
            "total_documents": 0,
            "avg_tokens_per_chunk": 0,
            "min_tokens": 0,
            "max_tokens": 0
        }
    
    token_counts = [chunk.get("token_count", 0) for chunk in chunks]
    unique_docs = set(chunk["filename"] for chunk in chunks)
    
    return {
        "total_chunks": len(chunks),
        "total_documents": len(unique_docs),
        "avg_tokens_per_chunk": sum(token_counts) // len(token_counts) if token_counts else 0,
        "min_tokens": min(token_counts) if token_counts else 0,
        "max_tokens": max(token_counts) if token_counts else 0,
        "documents": list(unique_docs)
    }
