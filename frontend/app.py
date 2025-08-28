from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-for-rag-pipeline'

API_BASE_URL = "http://localhost:8080"

def get_api_data(endpoint):
    """Helper function to make GET API calls"""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API Error: {e}")
        return None

def post_api_data(endpoint, data):
    """Helper function to make POST API calls"""
    try:
        response = requests.post(
            f"{API_BASE_URL}{endpoint}",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API Error: {e}")
        return None

@app.route('/')
def index():
    """Homepage - RAG Pipeline Interface"""
    # Check backend health
    health = get_api_data("/healthz")
    backend_status = "healthy" if health else "unhealthy"
    
    return render_template('index.html', backend_status=backend_status, health=health)

@app.route('/query', methods=['GET', 'POST'])
def query():
    """Query interface for asking questions"""
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        search_type = request.form.get('search_type', '')  
        size = int(request.form.get('size', 5))
        
        if not question:
            flash("Please enter a question", "error")
            return render_template('query.html')
        
        query_params = {
            "question": question,
            "type": "elser" if search_type == "elser" else "hybrid",
            "size": size
        }
        
        result = post_api_data("/query", query_params)
        
        if result:
            return render_template('query.html', 
                                 question=question, 
                                 search_type=query_params["type"],
                                 size=size,
                                 answer=result.get('answer'), 
                                 citations=result.get('citations', []))
        else:
            flash("Error getting answer from RAG system", "error")
            return render_template('query.html', question=question, search_type=query_params.get("type", "hybrid"), size=size)
    
    return render_template('query.html')

@app.route('/ingest', methods=['GET', 'POST'])
def ingest():
    """Document ingestion interface"""
    if request.method == 'POST':
        google_drive_url = request.form.get('google_drive_url', '').strip()
        
        if not google_drive_url:
            flash("Please enter a Google Drive URL", "error")
            return render_template('ingest.html')
        
        result = post_api_data("/ingest", {"google_drive_url": google_drive_url})
        
        if result:
            flash(f"Ingestion completed: {result.get('message', 'Success')}", "success")
            return render_template('ingest.html', 
                                 result=result, 
                                 google_drive_url=google_drive_url)
        else:
            flash("Error during document ingestion", "error")
    
    return render_template('ingest.html')

@app.route('/health')
def health_check():
    """Frontend health check that also checks backend"""
    backend_health = get_api_data("/healthz")
    
    return jsonify({
        "frontend": "healthy",
        "backend": backend_health if backend_health else "unhealthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api-docs')
def api_docs():
    """Redirect to FastAPI documentation"""
    return redirect(f"{API_BASE_URL}/docs")

@app.route('/api/query', methods=['POST'])
def api_query():
    """API endpoint for chat interface queries"""
    data = request.get_json()
    question = data.get('question', '').strip()
    search_type = data.get('type', 'hybrid')
    size = data.get('size', 5)
    
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    query_params = {
        "question": question,
        "type": search_type,
        "size": size
    }
    
    result = post_api_data("/query", query_params)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({"error": "Failed to get response from RAG system"}), 500

@app.route('/api/ingest', methods=['POST'])
def api_ingest():
    """API endpoint for chat interface document ingestion"""
    data = request.get_json()
    google_drive_url = data.get('google_drive_url', '').strip()
    
    if not google_drive_url:
        return jsonify({"error": "Google Drive URL is required"}), 400
    
    result = post_api_data("/ingest", {"google_drive_url": google_drive_url})
    
    if result:
        return jsonify(result)
    else:
        return jsonify({"error": "Failed to ingest documents"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
