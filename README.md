# Google Drive RAG Document System

A complete document processing and text extraction system that downloads documents from Google Drive, extracts text using PyMuPDF with OCR fallback, and provides intelligent document processing capabilities.

## 🚀 Features

- **📂 Google Drive Integration**: Automatic document download from public Google Drive folders
- **📄 Advanced PDF Processing**: Text extraction with PyMuPDF and OCR fallback using pytesseract
- **🔍 Smart Text Extraction**: Automatic OCR for pages with minimal text content (<50 characters)
- **📊 Comprehensive Metadata**: File information, download links, local paths, and extraction statistics
- **🐛 Debug Mode**: Separate debug files for download and extraction results
- **⚡ Health Monitoring**: System status monitoring
- **🔄 Modular Design**: Clean separation between download and text extraction processes

## 📁 Project Structure

```
hexaware-take-home-Digvijay/
├── backend/
│   ├── main.py                   # FastAPI server with ingest and query endpoints
│   ├── google_drive_utils.py     # Google Drive file download utilities
│   ├── pdf_utils.py              # PDF text extraction with OCR fallback
│   ├── requirements.txt          # Backend dependencies
│   ├── download_result.json      # Debug: Download results (when DEBUG=True)
│   ├── extraction_result.json    # Debug: Text extraction results (when DEBUG=True)
│   └── downloads/                # Downloaded PDF files
├── frontend/
│   ├── app.py                    # Flask web interface
│   ├── requirements.txt          # Frontend dependencies
│   └── templates/
│       ├── base.html             # Base template
│       ├── index.html            # Main interface
│       ├── ingest.html           # Document ingestion interface
│       └── query.html            # Query interface
├── .gitignore                    # Git ignore file
└── README.md                     # This file
```

## 🛠 Setup and Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Tesseract OCR engine (for OCR functionality)

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

- `POST /ingest` - Download documents from Google Drive and extract text
- `POST /query` - Submit a question and get an answer with citations (placeholder)
- `GET /healthz` - Health check endpoint

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
  "question": "What is the main topic of the documents?"
}
```

**Response:**
```json
{
  "answer": "This is a placeholder answer for: What is the main topic...",
  "citations": ["Document 1", "Document 2"]
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

### File Processing Workflow
1. **URL Parsing**: Extracts folder ID from Google Drive URLs
2. **File Discovery**: Finds all files in the public folder
3. **Download**: Downloads files to local storage
4. **Text Extraction**: Processes each PDF with OCR fallback
5. **Metadata Collection**: Gathers file information and statistics

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

### Start Both Applications:
```bash
# Terminal 1: Backend
cd backend && python main.py

# Terminal 2: Frontend  
cd frontend && python app.py
```

### Use the Document System:
1. **Open**: http://localhost:5001
2. **Ingest Documents**: Provide a public Google Drive folder URL
3. **Review Results**: Check downloaded files and extracted text
4. **Query Documents**: Ask questions about your indexed document content (placeholder)

### Test API Directly:
```bash
# Test ingest with a public Google Drive folder
curl -X POST "http://localhost:8080/ingest" \
     -H "Content-Type: application/json" \
     -d '{"google_drive_url": "https://drive.google.com/drive/folders/YOUR_FOLDER_ID"}'

# Test query endpoint
curl -X POST "http://localhost:8080/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is in the documents?"}'

# Health check
curl "http://localhost:8080/healthz"
```

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

### Performance Optimizations
- **Conditional OCR**: Only uses OCR when necessary (char_count < 50)
- **High-Resolution Processing**: 2x scaling for better OCR accuracy
- **Batch Processing**: Handles multiple files efficiently
- **Debug Caching**: Reuses results in debug mode for faster iteration

## 🔄 Future Enhancements

### RAG Implementation (Next Steps)
1. **Vector Database**: Add ChromaDB for document embeddings
2. **Embedding Model**: Integrate sentence transformers or OpenAI embeddings
3. **LLM Integration**: Connect to OpenAI GPT or local LLM for question answering
4. **Citation System**: Implement proper source attribution
5. **Query Processing**: Replace placeholder with actual RAG functionality

### Additional Features
1. **Authentication**: Add user authentication and authorization
2. **File Type Expansion**: Support for Word, Excel, PowerPoint documents
3. **Language Detection**: Multi-language OCR support
4. **Parallel Processing**: Concurrent file processing for large folders
5. **Progress Tracking**: Real-time processing status updates

## 📄 License

This project is open source and available under the MIT License.