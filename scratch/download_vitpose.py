#!/usr/bin/env python3
import os
import sys
import re
import zipfile
import requests
import json
import time

# Target folder
url_landing = "https://www.dropbox.com/scl/fo/a24ac4749h9qlpa9g0ghu/AJLIxkSrC93v4mtoSU3MUWg?dl=0&rlkey=kmluxze9dha4f78cyua3n0612"
extract_dir = "/Users/neilkloot/Code/Batting Sensor Stats/ViTPose/PoseData"
temp_zip = "scratch/temp_download.zip"

def get_cookies_and_csrf():
    print("==================================================================")
    print("🔑  Dropbox Authenticated Downloader Setup")
    print("==================================================================")
    print("Since this folder is too large for anonymous downloads, we need to")
    print("use your browser's session cookies to authorize the request.")
    print("\nHow to copy cookies:")
    print("1. Open the shared folder link in Google Chrome.")
    print("2. Press F12 (or Right-click -> Inspect) and go to the 'Network' tab.")
    print("3. Reload the page.")
    print("4. Click on the first network request (AJLIxkSrC93v4mtoSU3MUWg...).")
    print("5. In the 'Headers' panel, scroll down to 'Request Headers'.")
    print("6. Copy the entire text next to 'cookie:' (starting with 'gvc=...' or '__Host-js_csrf=...').")
    print("==================================================================\n")
    
    cookie_str = input("📋 Paste your 'cookie' header string here and press Enter:\n").strip()
    if not cookie_str:
        print("❌ Error: Cookie string cannot be empty.")
        sys.exit(1)
        
    session = requests.Session()
    session.headers.update({
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "cookie": cookie_str
    })
    
    # Establish session & get CSRF token
    print("\nEstablishing session...")
    session.get(url_landing)
    csrf_token = session.cookies.get("__Host-js_csrf")
    
    # Try parsing csrf from cookie string if session.cookies didn't grab it
    if not csrf_token:
        match = re.search(r'__Host-js_csrf=([^;]+)', cookie_str)
        if match:
            csrf_token = match.group(1)
            
    if not csrf_token:
        print("⚠️  Warning: Could not automatically detect CSRF token.")
        csrf_token = input("📋 Please manually paste the value of the '__Host-js_csrf' cookie:\n").strip()
        
    return session, csrf_token

def list_subfolders(session, csrf_token):
    print("📁 Fetching list of subfolders...")
    url_api = "https://www.dropbox.com/2/files/list_folder"
    headers_api = {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf_token,
        "X-Dropbox-Csrf-Token": csrf_token,
        "X-Csrf-Token": csrf_token,
    }
    payload = {
        "path": "",
        "shared_link": {
            "url": url_landing
        }
    }
    
    response = session.post(url_api, headers=headers_api, json=payload)
    if response.status_code != 200:
        print(f"❌ Failed to list folder (Status {response.status_code}): {response.text}")
        sys.exit(1)
        
    data = response.json()
    entries = [e for e in data.get("entries", []) if e.get(".tag") == "folder"]
    
    # Handle pagination if there are more folders (list_folder/continue)
    has_more = data.get("has_more", False)
    cursor = data.get("cursor")
    
    while has_more and cursor:
        url_cont = "https://www.dropbox.com/2/files/list_folder/continue"
        payload_cont = {"cursor": cursor}
        response_cont = session.post(url_cont, headers=headers_api, json=payload_cont)
        if response_cont.status_code == 200:
            data_cont = response_cont.json()
            entries.extend([e for e in data_cont.get("entries", []) if e.get(".tag") == "folder"])
            has_more = data_cont.get("has_more", False)
            cursor = data_cont.get("cursor")
        else:
            break
            
    return sorted(entries, key=lambda x: x["name"])

def download_subfolder(session, folder_name, idx, total):
    # Specify sub_path to download this folder specifically
    download_url = f"https://www.dropbox.com/scl/fo/a24ac4749h9qlpa9g0ghu/AJLIxkSrC93v4mtoSU3MUWg?dl=1&rlkey=kmluxze9dha4f78cyua3n0612&sub_path=/{folder_name}"
    print(f"[{idx}/{total}] 📥 Downloading {folder_name}...", end="", flush=True)
    
    try:
        response = session.get(download_url)
        if response.status_code == 200:
            # Check if we got HTML instead of a zip file
            if b"<!DOCTYPE html>" in response.content[:500] or b"<html" in response.content[:500]:
                print(" ❌ Error: Dropbox returned HTML instead of ZIP. Check cookies.")
                return False
                
            with open(temp_zip, 'wb') as f:
                f.write(response.content)
            
            # Extract
            target_path = os.path.join(extract_dir, folder_name)
            os.makedirs(target_path, exist_ok=True)
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(target_path)
                
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            print(" ✅ Done!")
            return True
        else:
            print(f" ❌ Error: Status Code {response.status_code}")
            return False
    except Exception as e:
        print(f" ❌ Error: {e}")
        return False

def main():
    session, csrf_token = get_cookies_and_csrf()
    subfolders = list_subfolders(session, csrf_token)
    
    total = len(subfolders)
    print(f"✅ Found {total} subfolders to download.")
    if total == 0:
        print("❌ No folders found. Make sure you pasted correct cookies.")
        sys.exit(1)
        
    os.makedirs("scratch", exist_ok=True)
    os.makedirs(extract_dir, exist_ok=True)
    
    success_count = 0
    for idx, folder in enumerate(subfolders, 1):
        name = folder["name"]
        success = download_subfolder(session, name, idx, total)
        if success:
            success_count += 1
        # Brief pause to avoid hammering the server
        time.sleep(1.0)
        
    print(f"\n========================================================")
    print(f"🎉 Completed! Successfully downloaded {success_count}/{total} folders.")
    print(f"Files are extracted to: {extract_dir}")
    print(f"========================================================")

if __name__ == "__main__":
    main()
