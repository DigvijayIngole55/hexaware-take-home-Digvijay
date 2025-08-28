import ollama
from typing import List, Dict, Optional
import json
import time
from prompts import get_answer_prompt

class OllamaClient:
    def __init__(self, model_name: str = "gemma3:4b", host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host
        self.client = ollama.Client(host=host)
        
        print(f"Initialized Ollama client for model: {model_name} at {host}")

    def _make_request(self, prompt: str, max_retries: int = 3) -> dict:
        for attempt in range(max_retries):
            try:
                response = self.client.generate(
                    model=self.model_name,
                    prompt=prompt,
                    options={
                        'temperature': 0.3,
                        'top_p': 0.9,
                        'max_tokens': 512
                    }
                )
                
                if response and 'response' in response:
                    return {"success": True, "data": response}
                else:
                    return {"success": False, "error": "Invalid response format"}
                    
            except ollama.ResponseError as e:
                error_msg = str(e)
                if "model not found" in error_msg.lower():
                    return {"success": False, "error": f"Model '{self.model_name}' not found. Please pull it first with: ollama pull {self.model_name}"}
                else:
                    print(f"Ollama API error: {error_msg}")
                    return {"success": False, "error": error_msg}
                    
            except Exception as e:
                print(f"Request failed: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
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
        
        context = "\n\n".join([f"Document {i+1}: {chunk}" for i, chunk in enumerate(context_chunks[:5])])
        
        prompt = get_answer_prompt(context, query)

        result = self._make_request(prompt)
        
        if result["success"]:
            try:
                response_data = result["data"]
                generated_text = response_data.get("response", "").strip()
                
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
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("Question:") and not line.startswith("Context:"):
                cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        
        if not result:
            result = text.strip()
        
        return result if result else "I was unable to generate a proper response."

    def test_connection(self) -> dict:
        print(f"Testing connection to Ollama with model: {self.model_name}...")
        
        try:
            models_response = self.client.list()
            available_models = [model.model for model in models_response.models]
            
            if self.model_name not in available_models:
                return {
                    "success": False, 
                    "error": f"Model '{self.model_name}' not found. Available models: {available_models}. Pull it with: ollama pull {self.model_name}"
                }
            
            result = self._make_request("Hello, how are you?")
            
            if result["success"]:
                print("✓ Connection test successful")
                return {"success": True, "message": "Connection successful"}
            else:
                print(f"✗ Connection test failed: {result.get('error')}")
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            error_msg = str(e)
            if "connection refused" in error_msg.lower():
                return {"success": False, "error": "Cannot connect to Ollama. Make sure Ollama is running with: ollama serve"}
            return {"success": False, "error": error_msg}

    def list_available_models(self) -> dict:
        try:
            models_response = self.client.list()
            available_models = [model.model for model in models_response.models]
            return {"success": True, "models": available_models}
        except Exception as e:
            return {"success": False, "error": str(e), "models": []}


def get_ollama_client(model_name: str = "gemma3:4b") -> OllamaClient:
    return OllamaClient(model_name=model_name)


def generate_answer_from_chunks(query: str, chunks: List[Dict], max_chunks: int = 5, model_name: str = "gemma3:4b") -> dict:
    if not chunks:
        return {
            "success": False,
            "answer": "No relevant documents found for your question.",
            "sources_used": 0
        }
    
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
    
    client = get_ollama_client(model_name)
    result = client.generate_answer(query, context_chunks)
    
    if result["success"]:
        result["sources_used"] = len(set(sources))  # Unique source count
        result["source_files"] = list(set(sources))
    
    return result