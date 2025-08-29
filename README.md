# Google Drive RAG Document System

A complete RAG (Retrieval-Augmented Generation) system that downloads documents from Google Drive, processes them with advanced text extraction and OCR, chunks and indexes them in Elasticsearch, and provides intelligent question-answering using local LLM models.

## 🚀 Features

- **📂 Google Drive Integration**: Automatic document download from public Google Drive folders
- **📄 Advanced PDF Processing**: Text extraction with PyMuPDF and OCR fallback using pytesseract
- **🔍 Smart Text Extraction**: Automatic OCR for pages with minimal text content (<50 characters)
- **📊 Intelligent Document Chunking**: Smart text segmentation for optimal RAG performance
- **🔍 Vector Search**: Elasticsearch-powered semantic search with sentence transformers
- **🤖 Local LLM Integration**: Ollama with Gemma 3 4B model for question answering
- **📝 RAG Pipeline**: Complete retrieval-augmented generation with source citations
- **⚡ Health Monitoring**: System status monitoring for all components
- **🔄 Modular Design**: Clean separation between ingestion, indexing, and query processes

## 📁 Project Structure

```
hexaware-take-home-Digvijay/
├── backend/
│   ├── main.py                   # FastAPI server with ingest and query endpoints
│   ├── google_drive_utils.py     # Google Drive file download utilities
│   ├── pdf_utils.py              # PDF text extraction with OCR fallback
│   ├── chunking_utils.py         # Text chunking utilities for RAG
│   ├── corpus_utils.py           # Document corpus management
│   ├── elasticsearch_utils.py    # Elasticsearch integration for vector search
│   ├── ollama_utils.py           # Ollama LLM client and utilities
│   ├── prompts.py                # LLM prompts for RAG pipeline
│   ├── requirements.txt          # Backend dependencies
│   └── downloads/                # Downloaded PDF files
├── frontend/
│   ├── app.py                    # Flask web interface
│   ├── requirements.txt          # Frontend dependencies
│   └── templates/
│       ├── base.html             # Base template
│       ├── index.html            # Main interface
│       ├── ingest.html           # Document ingestion interface
│       └── query.html            # Query interface
├── docker-compose.yml            # Docker services (Elasticsearch & Kibana)
├── .gitignore                    # Git ignore file
└── README.md                     # This file
```

## 🛠 Setup and Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Tesseract OCR engine (for OCR functionality)
- Ollama (for local LLM functionality)
- Docker & Docker Compose (for Elasticsearch/Kibana stack)

### Install Tesseract OCR

**On macOS:**
```bash
brew install tesseract
```

**On Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**On Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### Install Ollama (Local LLM)

**On macOS/Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**On Windows:**
Download and install from: https://ollama.ai/download

After installation, pull the required model:
```bash
ollama pull gemma3:4b
```

Start Ollama server:
```bash
ollama serve
```

### Docker Setup (Elasticsearch & Kibana)

Start the Elasticsearch and Kibana services:
```bash
docker-compose up -d
```

Verify services are running:
- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601

In Docker, Tesseract OCR is included automatically. For local development, you still need to install Tesseract manually.

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

### Core APIs

- `POST /ingest` - Download documents from Google Drive, extract text, chunk, and index to Elasticsearch
- `POST /query` - Submit a question and get an intelligent answer with source citations
- `GET /healthz` - Health check endpoint for all system components

### Request/Response Models

#### POST /ingest
**Request:**
```json
{
  "google_drive_url": "https://drive.google.com/drive/folders/1ABC123..."
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Downloaded 16 files, extracted text from 16",
  "documents_processed": 16,
  "files": [
    {
      "id": "1xKpBFi9B9lDkrbi_6ypHGM5q0lSIt29j",
      "name": "Accounting Basics.pdf",
      "download_link": "https://drive.google.com/uc?export=download&id=...",
      "local_path": "/path/to/downloads/Accounting Basics.pdf"
    }
  ],
  "extracted_texts": [
    {
      "file_id": "1xKpBFi9B9lDkrbi_6ypHGM5q0lSIt29j",
      "filename": "Accounting Basics.pdf",
      "filepath": "/path/to/downloads/Accounting Basics.pdf",
      "download_link": "https://drive.google.com/uc?export=download&id=...",
      "success": true,
      "text": "Full extracted text content...",
      "page_count": 45,
      "char_count": 125000,
      "word_count": 18500,
      "ocr_pages_count": 3,
      "pages": [
        {
          "page": 1,
          "text": "Page 1 content...",
          "char_count": 2500,
          "ocr_used": true,
          "original_char_count": 15
        }
      ],
      "metadata": {
        "title": "Accounting Basics",
        "author": "Nicolas Boucher"
      },
      "error": null
    }
  ]
}
```

#### POST /query
**Request:**
```json
{
  "question": "What is the main topic of the documents?",
  "type": "hybrid",
  "size": 5,
  "k": 60,
  "use_llm": true
}
```

**Response:**
```json
{
  "answer": "Based on the retrieved documents, the main topics covered include accounting principles, financial analysis, and business management fundamentals. The documents provide comprehensive coverage of...",
  "citations": ["Accounting Basics.pdf", "Financial Analysis Guide.pdf", "Business Management.pdf"],
  "sources_used": 3,
  "source_files": ["Accounting Basics.pdf", "Financial Analysis Guide.pdf", "Business Management.pdf"],
  "generation_method": "llm_generated"
}
```

## 📄 Document Processing

### Supported Document Types
- **PDF documents** (primary focus with OCR support)
- Word documents (.docx) - planned
- Text files (.txt) - planned
- Markdown files (.md) - planned

### Advanced PDF Processing Features

#### Text Extraction Pipeline
1. **Primary Extraction**: Uses PyMuPDF for fast text extraction
2. **OCR Fallback**: Automatically triggers pytesseract OCR for pages with <50 characters
3. **Smart Combination**: Merges original text with OCR results
4. **Detailed Tracking**: Reports which pages used OCR and extraction statistics

#### OCR Capabilities
- **Automatic Detection**: Triggers when page text is minimal
- **High Resolution**: Uses 2x matrix scaling for better OCR accuracy
- **Error Handling**: Graceful fallback if OCR fails
- **Statistics Tracking**: Reports OCR usage per document

### RAG Pipeline Workflow
1. **URL Parsing**: Extracts folder ID from Google Drive URLs
2. **File Discovery**: Finds all files in the public folder
3. **Download**: Downloads files to local storage
4. **Text Extraction**: Processes each PDF with OCR fallback
5. **Document Chunking**: Intelligently segments text for optimal retrieval
6. **Embedding Generation**: Creates vector embeddings using sentence transformers
7. **Elasticsearch Indexing**: Stores documents and embeddings for hybrid search
8. **Query Processing**: Performs semantic + keyword search for relevant chunks
9. **Answer Generation**: Uses Ollama LLM to generate contextual responses with citations

## 🔧 Configuration

### Debug Mode
Set `DEBUG = True` in main.py to enable:
- **Separate Debug Files**: `download_result.json` and `extraction_result.json`
- **Result Caching**: Reuses previous results for faster testing
- **Detailed Logging**: Enhanced debug information

### Supported File Extensions
```python
# Currently supported
PDF_EXTENSIONS = ['.pdf']

# File type detection patterns
SUPPORTED_PATTERNS = ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mp3']
```

## 🧪 Testing the System

### Start All Services:
```bash
# Terminal 1: Start Docker services (Elasticsearch & Kibana)
docker-compose up -d

# Terminal 2: Start Ollama server
ollama serve

# Terminal 3: Backend
cd backend && python main.py

# Terminal 4: Frontend  
cd frontend && python app.py
```

### Service URLs:
- **Frontend**: http://localhost:5001
- **Backend API**: http://localhost:8080
- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601
- **Ollama**: http://localhost:11434

### Use the RAG System:
1. **Open**: http://localhost:5001
2. **Ingest Documents**: Provide a public Google Drive folder URL to download, chunk, and index documents
3. **Review Results**: Check downloaded files, extracted text, and Elasticsearch indexing
4. **Query Documents**: Ask intelligent questions and get answers with source citations

### Test API Directly:
```bash
# Test ingest with a public Google Drive folder
curl -X POST "http://localhost:8080/ingest" \
     -H "Content-Type: application/json" \
     -d '{"google_drive_url": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID"}'

# Test query endpoint with RAG
curl -X POST "http://localhost:8080/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is in the documents?", "type": "hybrid", "use_llm": true}'

# Health check
curl "http://localhost:8080/healthz"
```

## 🏗️ RAG Architecture

### System Components
- **Document Ingestion**: Google Drive integration with PDF processing and OCR
- **Text Processing**: Intelligent chunking with tiktoken for optimal segment sizes
- **Vector Database**: Elasticsearch with dense vector support for semantic search
- **Embedding Model**: Sentence transformers for document and query vectorization
- **LLM Integration**: Ollama with Gemma 3 4B model for natural language generation
- **Hybrid Search**: Combines semantic vector search with keyword matching (RRF)

### Data Flow
```
Google Drive → Download → Extract Text → Chunk Documents → Generate Embeddings
                ↓
User Query → Vector Search + Keyword Search → Retrieve Relevant Chunks
                ↓
Context + Query → Ollama LLM → Generate Answer with Citations
```

### Search Methods
- **Hybrid Search**: Combines vector similarity and keyword matching using Reciprocal Rank Fusion (RRF)
- **Vector Search**: Semantic similarity using sentence transformer embeddings
- **Keyword Search**: Traditional BM25 scoring for exact term matches

## 📊 Technical Features

### Google Drive Integration
- **Public Folder Support**: Works with publicly accessible Google Drive folders
- **Automatic File Discovery**: Extracts file IDs and names from folder URLs
- **Direct Download**: Downloads files using Google Drive's export API
- **Multiple URL Formats**: Supports various Google Drive URL formats

### PDF Processing
- **PyMuPDF (fitz)**: Primary text extraction engine
- **pytesseract**: OCR engine for scanned/image-based PDFs
- **PIL/Pillow**: Image processing for OCR
- **Smart Detection**: Automatically determines when OCR is needed
- **Comprehensive Metadata**: Extracts PDF properties and statistics

### LLM Integration
- **Ollama**: Local LLM server for question answering
- **Gemma 3 4B**: Default model for generating responses
- **Elasticsearch**: Vector search and document storage
- **RAG Pipeline**: Retrieval-augmented generation for accurate answers

### Performance Optimizations
- **Conditional OCR**: Only uses OCR when necessary (char_count < 50)
- **High-Resolution Processing**: 2x scaling for better OCR accuracy
- **Batch Processing**: Handles multiple files efficiently
- **Debug Caching**: Reuses results in debug mode for faster iteration

## 🚀 Current RAG Features

### Implemented RAG Pipeline
1. **✅ Vector Database**: Elasticsearch for document embeddings and search
2. **✅ Embedding Model**: Sentence transformers for document vectorization  
3. **✅ LLM Integration**: Ollama with Gemma 3 4B model for question answering
4. **✅ Citation System**: Source attribution with document references
5. **✅ Query Processing**: Full RAG functionality with context-aware responses

## 🔄 Future Enhancements

### Additional Features
1. **Authentication**: Add user authentication and authorization
2. **File Type Expansion**: Support for Word, Excel, PowerPoint documents
3. **Language Detection**: Multi-language OCR support
4. **Parallel Processing**: Concurrent file processing for large folders
5. **Progress Tracking**: Real-time processing status updates

## 📄 License

This project is open source and available under the MIT License.