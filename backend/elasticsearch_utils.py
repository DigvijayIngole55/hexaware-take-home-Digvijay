import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk


def get_elasticsearch_client() -> Elasticsearch:
    print("Creating Elasticsearch client connection...")
    es = Elasticsearch(
        [{'host': 'localhost', 'port': 9200, 'scheme': 'http'}],
        timeout=30,
        max_retries=10,
        retry_on_timeout=True
    )
    print("Elasticsearch client created successfully")
    return es


def create_chunks_index(index_name: str = "hexaware_chunks") -> bool:
    print(f"Creating Elasticsearch index: {index_name}")
    es = get_elasticsearch_client()
    
    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "text_analyzer": {
                        "type": "standard",
                        "stopwords": "_english_"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "chunk_id": {
                    "type": "keyword"
                },
                "filename": {
                    "type": "keyword"
                },
                "drive_url": {
                    "type": "keyword"
                },
                "raw_text": {
                    "type": "text",
                    "analyzer": "text_analyzer"
                },
                "dense_vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine"
                },
                "text_for_elser": {
                    "type": "text"
                },
                "metadata": {
                    "properties": {
                        "filename": {
                            "type": "keyword"
                        },
                        "drive_url": {
                            "type": "keyword"
                        },
                        "chunk_id": {
                            "type": "keyword"
                        },
                        "chunk_index": {
                            "type": "integer"
                        },
                        "total_chunks": {
                            "type": "integer"
                        },
                        "token_count": {
                            "type": "integer"
                        }
                    }
                },
                "indexed_at": {
                    "type": "date"
                }
            }
        }
    }
    
    try:
        if es.indices.exists(index=index_name):
            print(f"Index {index_name} already exists, deleting...")
            es.indices.delete(index=index_name)
        
        print(f"Creating new index {index_name} with mapping...")
        es.indices.create(index=index_name, body=mapping)
        print(f"Index {index_name} created successfully")
        return True
    except Exception as e:
        print(f"Error creating index {index_name}: {e}")
        return False


def index_chunks(chunks: List[Dict], index_name: str = "hexaware_chunks") -> Dict[str, any]:
    print(f"Starting to index {len(chunks)} chunks to {index_name}")
    es = get_elasticsearch_client()
    
    if not chunks:
        print("No chunks provided for indexing")
        return {"success": False, "message": "No chunks to index", "indexed_count": 0}
    
    print("Preparing documents for bulk indexing...")
    docs = []
    for i, chunk in enumerate(chunks):
        if i == 0:
            print(f"First chunk ID: {chunk.get('chunk_id', 'unknown')}")
        doc = {
            "_index": index_name,
            "_id": chunk["chunk_id"],
            "_source": {
                **chunk,
                "indexed_at": datetime.now().isoformat()
            }
        }
        docs.append(doc)
    print(f"Prepared {len(docs)} documents for indexing")
    
    try:
        print("Starting bulk indexing...")
        success_count, failed = bulk(es, docs, refresh=True)
        print(f"Bulk indexing completed. Success: {success_count}, Failed: {len(failed)}")
        
        return {
            "success": True,
            "message": f"Successfully indexed {success_count} chunks",
            "indexed_count": success_count,
            "failed_count": len(failed)
        }
    except Exception as e:
        print(f"Error during bulk indexing: {str(e)}")
        return {
            "success": False,
            "message": f"Error indexing chunks: {str(e)}",
            "indexed_count": 0
        }


def get_index_stats(index_name: str = "hexaware_chunks") -> Dict[str, any]:
    print(f"Getting stats for index: {index_name}")
    es = get_elasticsearch_client()
    
    try:
        if not es.indices.exists(index=index_name):
            print(f"Index {index_name} does not exist")
            return {"exists": False, "message": "Index does not exist"}
        
        stats = es.indices.stats(index=index_name)
        count = es.count(index=index_name)
        doc_count = count['count']
        size_mb = round(stats['indices'][index_name]['total']['store']['size_in_bytes'] / (1024 * 1024), 2)
        
        print(f"Index {index_name} stats: {doc_count} documents, {size_mb} MB")
        
        return {
            "exists": True,
            "document_count": doc_count,
            "index_size_bytes": stats['indices'][index_name]['total']['store']['size_in_bytes'],
            "index_size_mb": size_mb
        }
    except Exception as e:
        print(f"Error getting index stats: {e}")
        return {"exists": False, "error": str(e)}


def delete_index(index_name: str = "hexaware_chunks") -> bool:
    es = get_elasticsearch_client()
    
    try:
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)
            return True
        return False
    except Exception as e:
        return False


def search_bm25(query: str, index_name: str = "hexaware_chunks", size: int = 5, min_score: float = 0.1) -> Dict[str, any]:
    """
    Perform BM25 text search using Elasticsearch match query.
    
    Args:
        query: The search query text
        index_name: Elasticsearch index name
        size: Number of results to return
        min_score: Minimum relevance score threshold
        
    Returns:
        Dictionary containing search results and metadata
    """
    print(f"Performing BM25 search for query: '{query}' in index: {index_name}")
    es = get_elasticsearch_client()
    
    search_body = {
        "query": {
            "bool": {
                "should": [
                    {
                        "match": {
                            "raw_text": {
                                "query": query,
                                "boost": 2.0
                            }
                        }
                    },
                    {
                        "match": {
                            "filename": {
                                "query": query,
                                "boost": 1.5
                            }
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        },
        "size": size,
        "min_score": min_score,
        "_source": {
            "excludes": ["dense_vector"]
        },
        "highlight": {
            "fields": {
                "raw_text": {
                    "fragment_size": 200,
                    "number_of_fragments": 3
                }
            }
        }
    }
    
    try:
        response = es.search(index=index_name, body=search_body)
        
        results = []
        for hit in response['hits']['hits']:
            result = {
                "chunk_id": hit['_source']['chunk_id'],
                "filename": hit['_source']['filename'],
                "drive_url": hit['_source'].get('drive_url', ''),
                "raw_text": hit['_source']['raw_text'][:500] + "..." if len(hit['_source']['raw_text']) > 500 else hit['_source']['raw_text'],
                "score": hit['_score'],
                "metadata": hit['_source'].get('metadata', {}),
                "highlights": hit.get('highlight', {})
            }
            results.append(result)
        
        print(f"BM25 search completed. Found {len(results)} results")
        
        return {
            "success": True,
            "search_type": "bm25",
            "query": query,
            "total_hits": response['hits']['total']['value'],
            "max_score": response['hits']['max_score'],
            "results": results,
            "took_ms": response['took']
        }
        
    except Exception as e:
        print(f"Error performing BM25 search: {e}")
        return {
            "success": False,
            "search_type": "bm25",
            "query": query,
            "error": str(e),
            "results": []
        }


def search_dense_vector(query_vector: List[float], index_name: str = "hexaware_chunks", size: int = 5) -> Dict[str, any]:
    """
    Perform dense vector search using Elasticsearch kNN query.
    
    Args:
        query_vector: The query embedding vector (384 dimensions)
        index_name: Elasticsearch index name
        size: Number of results to return
        
    Returns:
        Dictionary containing search results and metadata
    """
    print(f"Performing dense vector search in index: {index_name}")
    es = get_elasticsearch_client()
    
    if len(query_vector) != 384:
        return {
            "success": False,
            "search_type": "dense_vector",
            "error": f"Query vector must have 384 dimensions, got {len(query_vector)}",
            "results": []
        }
    
    search_body = {
        "knn": {
            "field": "dense_vector",
            "query_vector": query_vector,
            "k": size,
            "num_candidates": size * 10
        },
        "size": size,
        "_source": {
            "excludes": ["dense_vector"]
        }
    }
    
    try:
        response = es.search(index=index_name, body=search_body)
        
        results = []
        for hit in response['hits']['hits']:
            result = {
                "chunk_id": hit['_source']['chunk_id'],
                "filename": hit['_source']['filename'],
                "drive_url": hit['_source'].get('drive_url', ''),
                "raw_text": hit['_source']['raw_text'][:500] + "..." if len(hit['_source']['raw_text']) > 500 else hit['_source']['raw_text'],
                "score": hit['_score'],
                "metadata": hit['_source'].get('metadata', {})
            }
            results.append(result)
        
        print(f"Dense vector search completed. Found {len(results)} results")
        
        return {
            "success": True,
            "search_type": "dense_vector",
            "total_hits": response['hits']['total']['value'],
            "max_score": response['hits']['max_score'],
            "results": results,
            "took_ms": response['took']
        }
        
    except Exception as e:
        print(f"Error performing dense vector search: {e}")
        return {
            "success": False,
            "search_type": "dense_vector",
            "error": str(e),
            "results": []
        }


def search_elser(query: str, index_name: str = "hexaware_chunks", size: int = 5, min_score: float = 0.1) -> Dict[str, any]:
    """
    Perform ELSER semantic search using Elasticsearch text_expansion query.
    Note: This requires ELSER model to be deployed in Elasticsearch.
    
    Args:
        query: The search query text
        index_name: Elasticsearch index name
        size: Number of results to return
        min_score: Minimum relevance score threshold
        
    Returns:
        Dictionary containing search results and metadata
    """
    print(f"Performing ELSER search for query: '{query}' in index: {index_name}")
    es = get_elasticsearch_client()
    
    search_body = {
        "query": {
            "text_expansion": {
                "text_for_elser": {
                    "model_id": ".elser_model_2",
                    "model_text": query
                }
            }
        },
        "size": size,
        "min_score": min_score,
        "_source": {
            "excludes": ["dense_vector", "text_for_elser"]
        }
    }
    
    try:
        response = es.search(index=index_name, body=search_body)
        
        results = []
        for hit in response['hits']['hits']:
            result = {
                "chunk_id": hit['_source']['chunk_id'],
                "filename": hit['_source']['filename'],
                "drive_url": hit['_source'].get('drive_url', ''),
                "raw_text": hit['_source']['raw_text'][:500] + "..." if len(hit['_source']['raw_text']) > 500 else hit['_source']['raw_text'],
                "score": hit['_score'],
                "metadata": hit['_source'].get('metadata', {})
            }
            results.append(result)
        
        print(f"ELSER search completed. Found {len(results)} results")
        
        return {
            "success": True,
            "search_type": "elser",
            "query": query,
            "total_hits": response['hits']['total']['value'],
            "max_score": response['hits']['max_score'],
            "results": results,
            "took_ms": response['took']
        }
        
    except Exception as e:
        print(f"Error performing ELSER search: {e}")
        return {
            "success": False,
            "search_type": "elser",
            "query": query,
            "error": str(e),
            "results": []
        }


def calculate_rrf_score(rank: int, k: int = 60) -> float:
    """
    Calculate Reciprocal Rank Fusion (RRF) score.
    
    Args:
        rank: Position in the ranking (0-based)
        k: RRF constant (typically 60)
        
    Returns:
        RRF score
    """
    return 1.0 / (k + rank + 1)


def search_hybrid_rrf(query: str, query_vector: Optional[List[float]] = None, index_name: str = "hexaware_chunks", 
                     size: int = 5, k: int = 60) -> Dict[str, any]:
    """
    Perform hybrid search using Reciprocal Rank Fusion (RRF) to combine BM25, dense vector, and ELSER search results.
    
    Args:
        query: The search query text
        query_vector: Optional query embedding vector for dense search
        index_name: Elasticsearch index name
        size: Number of final results to return
        k: RRF constant (typically 60)
        
    Returns:
        Dictionary containing RRF-ranked search results and metadata
    """
    print(f"Performing RRF hybrid search for query: '{query}' in index: {index_name}")
    
    search_size = min(size * 3, 50)  # Get more results for better RRF
    
    bm25_results = search_bm25(query, index_name, search_size, min_score=0.0)
    bm25_chunks = {result['chunk_id']: {'result': result, 'rank': i} 
                   for i, result in enumerate(bm25_results.get('results', []))}
    
    dense_chunks = {}
    if query_vector and len(query_vector) == 384:
        dense_results = search_dense_vector(query_vector, index_name, search_size)
        dense_chunks = {result['chunk_id']: {'result': result, 'rank': i} 
                       for i, result in enumerate(dense_results.get('results', []))}
    
    elser_results = search_elser(query, index_name, search_size, min_score=0.0)
    elser_chunks = {result['chunk_id']: {'result': result, 'rank': i} 
                   for i, result in enumerate(elser_results.get('results', []))}
    
    all_chunks = set()
    all_chunks.update(bm25_chunks.keys())
    all_chunks.update(dense_chunks.keys())
    all_chunks.update(elser_chunks.keys())
    
    rrf_scores = {}
    for chunk_id in all_chunks:
        rrf_score = 0.0
        
        if chunk_id in bm25_chunks:
            rrf_score += calculate_rrf_score(bm25_chunks[chunk_id]['rank'], k)
        
        if chunk_id in dense_chunks:
            rrf_score += calculate_rrf_score(dense_chunks[chunk_id]['rank'], k)
        
        if chunk_id in elser_chunks:
            rrf_score += calculate_rrf_score(elser_chunks[chunk_id]['rank'], k)
        
        result_data = None
        if chunk_id in elser_chunks:
            result_data = elser_chunks[chunk_id]['result']
        elif chunk_id in dense_chunks:
            result_data = dense_chunks[chunk_id]['result']
        elif chunk_id in bm25_chunks:
            result_data = bm25_chunks[chunk_id]['result']
        
        if result_data:
            rrf_scores[chunk_id] = {
                'rrf_score': rrf_score,
                'result': result_data,
                'found_in': {
                    'bm25': chunk_id in bm25_chunks,
                    'dense': chunk_id in dense_chunks,
                    'elser': chunk_id in elser_chunks
                }
            }
    
    sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1]['rrf_score'], reverse=True)[:size]
    
    final_results = []
    for chunk_id, data in sorted_results:
        result = data['result'].copy()
        result['rrf_score'] = data['rrf_score']
        result['found_in'] = data['found_in']
        final_results.append(result)
    
    print(f"RRF hybrid search completed. Found {len(final_results)} results")
    
    return {
        "success": True,
        "search_type": "hybrid_rrf",
        "query": query,
        "rrf_k": k,
        "total_candidates": len(all_chunks),
        "search_stats": {
            "bm25_results": len(bm25_results.get('results', [])),
            "dense_results": len(dense_results.get('results', [])) if query_vector else 0,
            "elser_results": len(elser_results.get('results', []))
        },
        "results": final_results,
        "took_ms": (bm25_results.get('took_ms', 0) + 
                   (dense_results.get('took_ms', 0) if query_vector else 0) + 
                   elser_results.get('took_ms', 0))
    }


def search_hybrid(query: str, query_vector: Optional[List[float]] = None, index_name: str = "hexaware_chunks", 
                 size: int = 5, bm25_weight: float = 0.2, dense_weight: float = 0.3, elser_weight: float = 0.5) -> Dict[str, any]:
    """
    Perform hybrid search combining BM25, dense vector, and ELSER search methods.
    
    Args:
        query: The search query text
        query_vector: Optional query embedding vector for dense search
        index_name: Elasticsearch index name
        size: Number of results to return
        bm25_weight: Weight for BM25 search results (0.0-1.0)
        dense_weight: Weight for dense vector search results (0.0-1.0)
        elser_weight: Weight for ELSER search results (0.0-1.0)
        
    Returns:
        Dictionary containing combined search results and metadata
    """
    print(f"Performing hybrid search for query: '{query}' in index: {index_name}")
    
    total_weight = bm25_weight + dense_weight + elser_weight
    if total_weight > 0:
        bm25_weight /= total_weight
        dense_weight /= total_weight
        elser_weight /= total_weight
    
    es = get_elasticsearch_client()
    
    should_queries = []
    
    if bm25_weight > 0:
        should_queries.append({
            "bool": {
                "should": [
                    {
                        "match": {
                            "raw_text": {
                                "query": query,
                                "boost": bm25_weight * 2.0
                            }
                        }
                    },
                    {
                        "match": {
                            "filename": {
                                "query": query,
                                "boost": bm25_weight * 1.5
                            }
                        }
                    }
                ]
            }
        })
    
    if elser_weight > 0:
        should_queries.append({
            "text_expansion": {
                "text_for_elser": {
                    "model_id": ".elser_model_2",
                    "model_text": query,
                    "boost": elser_weight
                }
            }
        })
    
    search_body = {
        "query": {
            "bool": {
                "should": should_queries,
                "minimum_should_match": 1
            }
        },
        "size": size,
        "_source": {
            "excludes": ["dense_vector", "text_for_elser"]
        }
    }
    
    if query_vector and len(query_vector) == 384 and dense_weight > 0:
        search_body["knn"] = {
            "field": "dense_vector",
            "query_vector": query_vector,
            "k": size,
            "num_candidates": size * 10,
            "boost": dense_weight
        }
    
    try:
        response = es.search(index=index_name, body=search_body)
        
        results = []
        for hit in response['hits']['hits']:
            result = {
                "chunk_id": hit['_source']['chunk_id'],
                "filename": hit['_source']['filename'],
                "drive_url": hit['_source'].get('drive_url', ''),
                "raw_text": hit['_source']['raw_text'][:500] + "..." if len(hit['_source']['raw_text']) > 500 else hit['_source']['raw_text'],
                "score": hit['_score'],
                "metadata": hit['_source'].get('metadata', {})
            }
            results.append(result)
        
        print(f"Hybrid search completed. Found {len(results)} results")
        
        return {
            "success": True,
            "search_type": "hybrid",
            "query": query,
            "weights": {
                "bm25": bm25_weight,
                "dense": dense_weight,
                "elser": elser_weight
            },
            "total_hits": response['hits']['total']['value'],
            "max_score": response['hits']['max_score'],
            "results": results,
            "took_ms": response['took']
        }
        
    except Exception as e:
        print(f"Error performing hybrid search: {e}")
        return {
            "success": False,
            "search_type": "hybrid",
            "query": query,
            "error": str(e),
            "results": []
        }
