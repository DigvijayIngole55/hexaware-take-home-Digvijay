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
        print(f"DEBUG: Accessing public folder URL: {folder_url}")
        
        folder_id = extract_folder_id_from_url(folder_url)
        print(f"DEBUG: Extracted folder ID: {folder_id}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(folder_url, headers=headers)
        print(f"DEBUG: Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"DEBUG: Failed to access folder - Status code: {response.status_code}")
            return []
        
        response_text = response.text
        print(f"DEBUG: Successfully accessed folder - Response length: {len(response_text)}")
        
        print(f"DEBUG: Response content preview (first 1000 chars):")
        print(response_text[:1000])
        print(f"DEBUG: Response content end preview (last 500 chars):")
        print(response_text[-500:])
        
        files = []
        
        json_patterns = [
            r'\["([a-zA-Z0-9-_]{25,})",[^,]*,"([^"]*\.(?:pdf|doc|docx|txt|xlsx|ppt|pptx|jpg|jpeg|png|gif|mp4|mp3))"',
            r'"([a-zA-Z0-9-_]{25,})"[^}]*"name"\s*:\s*"([^"]+)"',
            r'\["([a-zA-Z0-9-_]{25,})"[^,]*,[^,]*,"([^"]+\.[^"]+)"',
        ]
        
        for i, pattern in enumerate(json_patterns):
            matches = re.findall(pattern, response_text, re.IGNORECASE)
            if matches:
                print(f"DEBUG: Found {len(matches)} files using JSON pattern {i+1}")
                for file_id, file_name in matches[:20]:
                    if file_name and '.' in file_name:
                        files.append({"id": file_id, "name": file_name})
                break
        
        if not files:
            print("DEBUG: No files found with JSON patterns - using basic fallback")
            id_pattern = r'"([a-zA-Z0-9-_]{25,44})"'
            all_ids = re.findall(id_pattern, response_text)
            unique_ids = list(set(all_ids))[:20]
            
            for i, file_id in enumerate(unique_ids):
                files.append({
                    "id": file_id,
                    "name": f"document_{i+1}.pdf"
                })
        
        seen_ids = set()
        unique_files = []
        for file_info in files:
            if file_info["id"] not in seen_ids:
                seen_ids.add(file_info["id"])
                unique_files.append(file_info)
        
        files = unique_files
        
        print(f"DEBUG: Final files array ({len(files)} files):")
        for i, file_info in enumerate(files):
            print(f"  File {i+1}: ID={file_info['id']}, Name={file_info['name']}")
        
        print(f"DEBUG: Returning files array: {files}")
        return files
        
    except Exception as e:
        print(f"DEBUG: Exception in get_files_from_folder: {str(e)}")
        return []




def download_file(file_id: str, file_name: str, download_folder: str) -> bool:
    try:
        print(f"DEBUG: Starting download - File ID: {file_id}, Name: {file_name}")
        os.makedirs(download_folder, exist_ok=True)
        
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        print(f"DEBUG: Download URL: {download_url}")
        
        session = requests.Session()
        response = session.get(download_url, stream=True)
        print(f"DEBUG: Initial response status: {response.status_code}")
        
        if 'virus scan warning' in response.text.lower():
            print("DEBUG: Virus scan warning detected, getting confirm token")
            token_match = re.search(r'name="confirm" value="([^"]+)"', response.text)
            if token_match:
                token = token_match.group(1)
                download_url = f"https://drive.google.com/uc?export=download&confirm={token}&id={file_id}"
                print(f"DEBUG: Using confirm token: {token}")
                response = session.get(download_url, stream=True)
                print(f"DEBUG: Confirmed response status: {response.status_code}")
        
        file_path = os.path.join(download_folder, file_name)
        print(f"DEBUG: Saving to: {file_path}")
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=32768):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(file_path)
        print(f"DEBUG: Downloaded {file_name} - Size: {file_size} bytes")
        return True
        
    except Exception as e:
        print(f"DEBUG: Exception downloading {file_name}: {str(e)}")
        return False


def download_all_files_from_folder(folder_url: str, download_folder: str = "downloads") -> Dict[str, any]:
    try:
        print(f"DEBUG: Starting download_all_files_from_folder")
        print(f"DEBUG: Folder URL: {folder_url}")
        print(f"DEBUG: Download folder: {download_folder}")
        
        files = get_files_from_folder(folder_url)
        
        if not files:
            print("DEBUG: No files found in folder")
            return {
                "success": False,
                "message": "No files found in folder",
                "count": 0
            }
        
        print(f"DEBUG: Found {len(files)} files to download")
        downloaded_count = 0
        
        for i, file_info in enumerate(files):
            print(f"DEBUG: Processing file {i+1}/{len(files)}")
            if download_file(file_info["id"], file_info["name"], download_folder):
                downloaded_count += 1
                print(f"DEBUG: Successfully downloaded file {i+1}")
            else:
                print(f"DEBUG: Failed to download file {i+1}")
        
        print(f"DEBUG: Download complete - {downloaded_count}/{len(files)} files downloaded")
        
        if downloaded_count > 0:
            return {
                "success": True,
                "message": f"Downloaded {downloaded_count} PDF files",
                "count": downloaded_count
            }
        else:
            return {
                "success": False,
                "message": "No files could be downloaded",
                "count": 0
            }
            
    except Exception as e:
        print(f"DEBUG: Exception in download_all_files_from_folder: {str(e)}")
        return {
            "success": False,
            "message": "Error processing folder",
            "count": 0
        }