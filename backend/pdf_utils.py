import os
import io
import fitz
import pytesseract
from PIL import Image
from typing import List, Dict, Optional


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        if not os.path.exists(pdf_path):
            return ""
        
        doc = fitz.open(pdf_path)
        text = ""
        
        for page in doc:
            text += page.get_text()
        
        doc.close()
        return text.strip()
    
    except Exception as e:
        return ""


def extract_text_with_ocr_fallback(page, page_num: int) -> Dict[str, any]:
    try:

        page_text = page.get_text()
        

        if len(page_text.strip()) < 50:
            try:

                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                

                image = Image.open(io.BytesIO(img_data))
                

                ocr_text = pytesseract.image_to_string(image, config='--psm 6')
                

                combined_text = page_text + "\n" + ocr_text if page_text.strip() else ocr_text
                
                return {
                    "page": page_num + 1,
                    "text": combined_text.strip(),
                    "char_count": len(combined_text),
                    "ocr_used": True,
                    "original_char_count": len(page_text)
                }
            except Exception as ocr_error:

                return {
                    "page": page_num + 1,
                    "text": page_text.strip(),
                    "char_count": len(page_text),
                    "ocr_used": False,
                    "ocr_error": str(ocr_error)
                }
        else:
            return {
                "page": page_num + 1,
                "text": page_text.strip(),
                "char_count": len(page_text),
                "ocr_used": False
            }
    except Exception as e:
        return {
            "page": page_num + 1,
            "text": "",
            "char_count": 0,
            "ocr_used": False,
            "error": str(e)
        }

def extract_text_with_metadata(pdf_path: str) -> Dict[str, any]:
    try:
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "text": "",
                "page_count": 0,
                "metadata": {},
                "error": "File not found"
            }
        
        doc = fitz.open(pdf_path)
        text = ""
        page_texts = []
        ocr_pages_count = 0
        
        for page_num, page in enumerate(doc):
            page_result = extract_text_with_ocr_fallback(page, page_num)
            text += page_result["text"] + "\n"
            page_texts.append(page_result)
            
            if page_result.get("ocr_used", False):
                ocr_pages_count += 1
        
        metadata = doc.metadata
        page_count = doc.page_count
        doc.close()
        
        return {
            "success": True,
            "text": text.strip(),
            "page_count": page_count,
            "pages": page_texts,
            "metadata": metadata,
            "char_count": len(text),
            "word_count": len(text.split()) if text else 0,
            "ocr_pages_count": ocr_pages_count,
            "error": None
        }
    
    except Exception as e:
        return {
            "success": False,
            "text": "",
            "page_count": 0,
            "metadata": {},
            "error": str(e)
        }


def extract_text_from_multiple_pdfs(pdf_paths: List[str]) -> List[Dict[str, any]]:
    results = []
    
    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        result = extract_text_with_metadata(pdf_path)
        result["filename"] = filename
        result["filepath"] = pdf_path
        results.append(result)
    
    return results


def extract_text_from_files_list(files: List[Dict[str, str]]) -> List[Dict[str, any]]:
    results = []
    
    for file_info in files:
        local_path = file_info.get("local_path", "")
        if not local_path or not os.path.exists(local_path):
            results.append({
                "file_id": file_info.get("id", ""),
                "filename": file_info.get("name", ""),
                "filepath": local_path,
                "success": False,
                "text": "",
                "page_count": 0,
                "error": "File not found or path empty"
            })
            continue
        
        result = extract_text_with_metadata(local_path)
        result["file_id"] = file_info.get("id", "")
        result["filename"] = file_info.get("name", "")
        result["filepath"] = local_path
        result["download_link"] = file_info.get("download_link", "")
        
        results.append(result)
    
    return results


def get_pdf_summary(pdf_path: str) -> Dict[str, any]:
    try:
        if not os.path.exists(pdf_path):
            return {"error": "File not found"}
        
        doc = fitz.open(pdf_path)
        
        summary = {
            "filename": os.path.basename(pdf_path),
            "page_count": doc.page_count,
            "metadata": doc.metadata,
            "file_size": os.path.getsize(pdf_path),
            "pages_summary": []
        }
        
        for page_num, page in enumerate(doc):
            page_text = page.get_text()
            summary["pages_summary"].append({
                "page": page_num + 1,
                "char_count": len(page_text),
                "word_count": len(page_text.split()) if page_text else 0,
                "has_text": bool(page_text.strip())
            })
        
        doc.close()
        
        total_chars = sum(p["char_count"] for p in summary["pages_summary"])
        total_words = sum(p["word_count"] for p in summary["pages_summary"])
        
        summary["total_chars"] = total_chars
        summary["total_words"] = total_words
        summary["avg_words_per_page"] = total_words / doc.page_count if doc.page_count > 0 else 0
        
        return summary
    
    except Exception as e:
        return {"error": str(e)}
