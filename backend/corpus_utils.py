import os
import json
from typing import List, Dict
from datetime import datetime


def create_corpus_from_extraction(extraction_results: List[Dict]) -> List[Dict[str, str]]:
    corpus = []
    
    for result in extraction_results:
        if result.get("success", False) and result.get("text"):
            corpus_item = {
                "pdf_name": result.get("filename", ""),
                "pdf_link": result.get("download_link", ""),
                "corpus": result.get("text", "").strip()
            }
            corpus.append(corpus_item)
    
    return corpus


def save_corpus_result(corpus: List[Dict[str, str]], url: str, debug_file: str = "cache/corpus_result.json"):
    try:
        cache_dir = os.path.dirname(debug_file)
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        debug_data = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "corpus_count": len(corpus),
            "corpus": corpus
        }
        
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        pass


def load_corpus_result(debug_file: str = "cache/corpus_result.json") -> List[Dict[str, str]]:
    if not os.path.exists(debug_file):
        return None
    
    try:
        with open(debug_file, 'r', encoding='utf-8') as f:
            debug_data = json.load(f)
            return debug_data.get("corpus")
    except Exception as e:
        return None


def create_corpus_summary(corpus: List[Dict[str, str]]) -> Dict[str, any]:
    if not corpus:
        return {
            "total_documents": 0,
            "total_corpus_length": 0,
            "average_corpus_length": 0,
            "documents": []
        }
    
    total_length = 0
    document_summaries = []
    
    for item in corpus:
        corpus_length = len(item.get("corpus", ""))
        word_count = len(item.get("corpus", "").split()) if item.get("corpus") else 0
        
        total_length += corpus_length
        
        document_summaries.append({
            "pdf_name": item.get("pdf_name", ""),
            "corpus_length": corpus_length,
            "word_count": word_count
        })
    
    return {
        "total_documents": len(corpus),
        "total_corpus_length": total_length,
        "average_corpus_length": total_length // len(corpus) if corpus else 0,
        "documents": document_summaries
    }


def filter_corpus_by_min_length(corpus: List[Dict[str, str]], min_length: int = 100) -> List[Dict[str, str]]:
    return [
        item for item in corpus 
        if len(item.get("corpus", "")) >= min_length
    ]


def get_corpus_statistics(corpus: List[Dict[str, str]]) -> Dict[str, any]:
    if not corpus:
        return {
            "document_count": 0,
            "total_characters": 0,
            "total_words": 0,
            "avg_characters_per_doc": 0,
            "avg_words_per_doc": 0,
            "min_length": 0,
            "max_length": 0
        }
    
    lengths = []
    word_counts = []
    
    for item in corpus:
        corpus_text = item.get("corpus", "")
        char_count = len(corpus_text)
        word_count = len(corpus_text.split()) if corpus_text else 0
        
        lengths.append(char_count)
        word_counts.append(word_count)
    
    total_chars = sum(lengths)
    total_words = sum(word_counts)
    
    return {
        "document_count": len(corpus),
        "total_characters": total_chars,
        "total_words": total_words,
        "avg_characters_per_doc": total_chars // len(corpus),
        "avg_words_per_doc": total_words // len(corpus),
        "min_length": min(lengths) if lengths else 0,
        "max_length": max(lengths) if lengths else 0
    }
