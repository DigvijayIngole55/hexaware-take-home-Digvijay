import os
import requests
import re
from typing import List, Dict


def extract_folder_id_from_url(folder_url: str) -> str:
    patterns = [
        r'/folders/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
        r'folderview\?id=([a-zA-Z0-9-_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, folder_url)
        if match:
            return match.group(1)
    return ""

def get_files_from_folder(folder_url: str) -> List[Dict[str, str]]:
    try:

        
        folder_id = extract_folder_id_from_url(folder_url)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(folder_url, headers=headers)

        
        if response.status_code != 200:
            return []
        
        response_text = response.text

        files = []
        
        json_patterns = [
            r'\["([a-zA-Z0-9-_]{25,})",[^,]*,"([^"]*\.(?:pdf|doc|docx|txt|xlsx|ppt|pptx|jpg|jpeg|png|gif|mp4|mp3))"',
            r'"([a-zA-Z0-9-_]{25,})"[^}]*"name"\s*:\s*"([^"]+)"',
            r'\["([a-zA-Z0-9-_]{25,})"[^,]*,[^,]*,"([^"]+\.[^"]+)"',
        ]
        
        for i, pattern in enumerate(json_patterns):
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            if matches:

                for file_id, file_name in matches[:20]:
                    if file_name and '.' in file_name:
                        download_link = f"https://drive.google.com/uc?export=download&id={file_id}"
                        files.append({
                            "id": file_id, 
                            "name": file_name,
                            "download_link": download_link,
                            "local_path": ""
                        })
                break
        
        if not files:
            id_pattern = r'"([a-zA-Z0-9-_]{25,44})"'
            all_ids = re.findall(id_pattern, response_text)
            unique_ids = list(set(all_ids))[:20]
            
            for i, file_id in enumerate(unique_ids):
                download_link = f"https://drive.google.com/uc?export=download&id={file_id}"
                files.append({
                    "id": file_id,
                    "name": f"document_{i+1}.pdf",
                    "download_link": download_link,
                    "local_path": ""
                })
        
        seen_ids = set()
        unique_files = []
        for file_info in files:
            if file_info["id"] not in seen_ids:
                seen_ids.add(file_info["id"])
                unique_files.append(file_info)
        
        files = unique_files

        return files
        
    except Exception as e:
        return []


def download_file(file_id: str, file_name: str, download_folder: str) -> tuple[bool, str]:
    try:

        os.makedirs(download_folder, exist_ok=True)
        
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        
        session = requests.Session()
        response = session.get(download_url, stream=True)

        
        if 'virus scan warning' in response.text.lower():
            token_match = re.search(r'name="confirm" value="([^"]+)"', response.text)
            if token_match:
                token = token_match.group(1)
                download_url = f"https://drive.google.com/uc?export=download&confirm={token}&id={file_id}"

                response = session.get(download_url, stream=True)

        
        file_path = os.path.join(download_folder, file_name)

        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(file_path)

        return True, file_path
        
    except Exception as e:
        return False, ""


def download_all_files_from_folder(folder_url: str, download_folder: str = "downloads") -> Dict[str, any]:
    try:

        
        files = get_files_from_folder(folder_url)
        
        if not files:
            return {
                "success": False,
                "message": "No files found in folder",
                "count": 0,
                "files": []
            }
        
        downloaded_count = 0
        
        for i, file_info in enumerate(files):

            success, local_path = download_file(file_info["id"], file_info["name"], download_folder)
            if success:
                downloaded_count += 1
                file_info["local_path"] = local_path

            else:
                file_info["local_path"] = ""
        
        if downloaded_count > 0:
            return {
                "success": True,
                "message": f"Downloaded {downloaded_count} PDF files",
                "count": downloaded_count,
                "files": files
            }
        else:
            return {
                "success": False,
                "message": "No files could be downloaded",
                "count": 0,
                "files": files
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": "Error processing folder",
            "count": 0,
            "files": []
        }