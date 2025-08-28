import os
import requests
from typing import List, Dict, Optional
import json
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class HuggingFaceClient:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "meta-llama/Llama-3.1-8B-Instruct"):
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        
        if not self.api_key:
            print("Warning: No Hugging Face API key found. Set HUGGINGFACE_API_KEY environment variable.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        } if self.api_key else {"Content-Type": "application/json"}
        
        print(f"Initialized Hugging Face client for model: {model_name}")

    def _make_request(self, payload: dict, max_retries: int = 3) -> dict:
        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                elif response.status_code == 503:
                    # Model is loading
                    estimated_time = response.json().get("estimated_time", 20)
                    print(f"Model is loading, waiting {estimated_time} seconds...")
                    time.sleep(estimated_time)
                    continue
                elif response.status_code == 429:
                    # Rate limit
                    print(f"Rate limited, waiting before retry {attempt + 1}/{max_retries}")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    error_msg = response.text
                    print(f"API request failed with status {response.status_code}: {error_msg}")
                    return {"success": False, "error": f"HTTP {response.status_code}: {error_msg}"}
                    
            except requests.exceptions.Timeout:
                print(f"Request timeout, retry {attempt + 1}/{max_retries}")
                time.sleep(1)
                continue
            except Exception as e:
                print(f"Request failed: {str(e)}")
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Max retries exceeded"}

    def generate_answer(self, query: str, context_chunks: List[str], max_length: int = 512) -> dict:
        print(f"Generating answer for query: '{query}' using {len(context_chunks)} context chunks")
        
        if not context_chunks:
            return {
                "success": False, 
                "error": "No context chunks provided",
                "answer": "I don't have enough information to answer your question."
            }
        
        # Prepare context
        context = "\n\n".join([f"Document {i+1}: {chunk}" for i, chunk in enumerate(context_chunks[:5])])
        
        # Create prompt for Llama-3-8B-Instruct
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful AI assistant. Answer the user's question based on the provided context documents. If the answer is not in the context, say so clearly.<|eot_id|><|start_header_id|>user<|end_header_id|>

Context:
{context}

Question: {query}

Please provide a comprehensive answer based on the context above.<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_length,
                "temperature": 0.3,
                "top_p": 0.9,
                "do_sample": True,
                "stop": ["<|eot_id|>", "<|end_of_text|>"],
                "return_full_text": False
            }
        }
        
        result = self._make_request(payload)
        
        if result["success"]:
            try:
                # Handle different response formats
                response_data = result["data"]
                if isinstance(response_data, list) and len(response_data) > 0:
                    generated_text = response_data[0].get("generated_text", "").strip()
                elif isinstance(response_data, dict):
                    generated_text = response_data.get("generated_text", "").strip()
                else:
                    generated_text = str(response_data).strip()
                
                # Clean up the response
                answer = self._clean_response(generated_text)
                
                print(f"Successfully generated answer: {answer[:100]}...")
                return {
                    "success": True,
                    "answer": answer,
                    "model": self.model_name,
                    "context_chunks_used": len(context_chunks)
                }
                
            except Exception as e:
                print(f"Error processing response: {str(e)}")
                return {
                    "success": False,
                    "error": f"Error processing response: {str(e)}",
                    "answer": "Sorry, I encountered an error processing the response."
                }
        else:
            print(f"Generation failed: {result.get('error', 'Unknown error')}")
            return {
                "success": False,
                "error": result.get("error", "Generation failed"),
                "answer": "Sorry, I couldn't generate an answer at this time."
            }

    def _clean_response(self, text: str) -> str:
        # Remove any remaining special tokens
        text = text.replace("<|start_header_id|>", "").replace("<|end_header_id|>", "")
        text = text.replace("<|eot_id|>", "").replace("<|end_of_text|>", "").strip()
        
        # Remove any repetitive patterns or artifacts
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("Question:") and not line.startswith("Context:"):
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        
        # Fallback if cleaning resulted in empty string
        if not result:
            result = text.strip()
        
        return result if result else "I was unable to generate a proper response."

    def test_connection(self) -> dict:
        print(f"Testing connection to {self.model_name}...")
        
        test_payload = {
            "inputs": "Hello, how are you?",
            "parameters": {
                "max_new_tokens": 50,
                "temperature": 0.3
            }
        }
        
        result = self._make_request(test_payload)
        
        if result["success"]:
            print("✓ Connection test successful")
            return {"success": True, "message": "Connection successful"}
        else:
            print(f"✗ Connection test failed: {result.get('error')}")
            return {"success": False, "error": result.get("error")}


def get_huggingface_client() -> HuggingFaceClient:
    return HuggingFaceClient()


def generate_answer_from_chunks(query: str, chunks: List[Dict], max_chunks: int = 5) -> dict:
    if not chunks:
        return {
            "success": False,
            "answer": "No relevant documents found for your question.",
            "sources_used": 0
        }
    
    # Extract text from chunks
    context_chunks = []
    sources = []
    
    for chunk in chunks[:max_chunks]:
        text = chunk.get('raw_text', '').strip()
        filename = chunk.get('filename', 'Unknown')
        
        if text:
            context_chunks.append(text)
            sources.append(filename)
    
    if not context_chunks:
        return {
            "success": False,
            "answer": "The retrieved documents don't contain readable text.",
            "sources_used": 0
        }
    
    # Generate answer
    client = get_huggingface_client()
    result = client.generate_answer(query, context_chunks)
    
    # Add source information
    if result["success"]:
        result["sources_used"] = len(set(sources))  # Unique source count
        result["source_files"] = list(set(sources))
    
    return result