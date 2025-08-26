# Google Drive RAG Document System

A document-based RAG (Retrieval-Augmented Generation) system that indexes documents from Google Drive and provides intelligent question-answering capabilities.

## 🚀 Features

- **📂 Google Drive Integration**: Direct document ingestion from Google Drive
- **📄 Document Processing**: Index and process various document types
- **🔍 Document-based Q&A**: Query indexed documents with contextual answers
- **📝 Citation System**: Source attribution for all answers
- **⚡ Health Monitoring**: System status monitoring

## 📁 Project Structure

```
hexaware-take-home-Digvijay/
├── backend/
│   ├── main.py              # FastAPI RAG API with 3 endpoints
│   └── requirements.txt     # Backend dependencies
├── frontend/
│   ├── app.py              # Flask web interface
│   ├── requirements.txt    # Frontend dependencies
│   └── templates/
│       ├── base.html       # Base template
│       └── index.html      # Main interface
└── README.md               # This file
```

## 🛠 Setup and Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the FastAPI server:
   ```bash
   python main.py
   ```

The backend API will be available at:
- **API**: http://localhost:8080
- **Interactive API docs**: http://localhost:8080/docs
- **Alternative docs**: http://localhost:8080/redoc

### Frontend Setup (Flask)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the Flask application:
   ```bash
   python app.py
   ```

The frontend will be available at: http://localhost:5001

## 📚 API Endpoints

### Core RAG APIs

- `POST /query` - Submit a question and get an answer with citations
- `POST /ingest` - Load/re-index documents from Google Drive  
- `GET /healthz` - Health check endpoint

### Request/Response Models

#### POST /query
**Request:**
```json
{
  "question": "What is the main topic of the documents?"
}
```

**Response:**
```json
{
  "answer": "The main topic is...",
  "citations": ["Document 1", "Document 2"]
}
```

#### POST /ingest
**Request:**
```json
{
  "google_drive_url": "https://drive.google.com/drive/folders/..."
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Successfully processed documents",
  "documents_processed": 5
}
```

## 📄 Document Processing

### Supported Document Types
- PDF documents
- Word documents (.docx)
- Text files (.txt)
- Markdown files (.md)
- Excel files (.xlsx)
- PowerPoint presentations (.pptx)

### RAG Pipeline
- **Ingestion**: Extract text from Google Drive documents
- **Indexing**: Create vector embeddings for document chunks
- **Retrieval**: Find relevant document sections for queries
- **Generation**: Generate answers with proper citations

## 🚦 Current Status: Skeleton Implementation

### ✅ Completed
- **Chat Interface**: Interactive messaging interface
- **API Skeleton**: All three required endpoints with proper schemas
- **Health Monitoring**: System health check functionality
- **Document Ingestion**: Interface for Google Drive URLs

### 🔄 Ready for RAG Implementation

When implementing the full RAG pipeline, add these dependencies:
```bash
# In backend/requirements.txt
google-api-python-client==2.108.0
google-auth==2.23.4
langchain==0.0.340
chromadb==0.4.18
sentence-transformers==2.2.2
openai==1.3.5
python-dotenv==1.0.0
```

### Implementation Roadmap
1. **Google Drive Integration**: Set up Drive API client and authentication
2. **Document Processing**: Extract text from PDFs, Word docs, etc.
3. **Vector Database**: Implement ChromaDB for document embeddings
4. **Embedding Model**: Add sentence transformers or OpenAI embeddings
5. **LLM Integration**: Connect to OpenAI GPT or local LLM
6. **Citation System**: Track and return document sources
7. **Production Setup**: Add authentication, logging, and error handling

## 🧪 Testing the Interface

### Start Both Applications:
```bash
# Terminal 1: Backend
cd backend && python main.py

# Terminal 2: Frontend  
cd frontend && python app.py
```

### Use the Document System:
1. **Open**: http://localhost:5001
2. **Ingest Documents**: Add Google Drive folder/file URLs to index documents
3. **Query Documents**: Ask questions about your indexed document content
4. **Review Citations**: See which documents provided the answers

### Test API Directly:
```bash
# Test query endpoint
curl -X POST "http://localhost:8080/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is RAG?"}'

# Test ingest endpoint
curl -X POST "http://localhost:8080/ingest" \
     -H "Content-Type: application/json" \
     -d '{"google_drive_url": "https://drive.google.com/test"}'
```



## 📄 License

This project is open source and available under the MIT License.