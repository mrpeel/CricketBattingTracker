#!/usr/bin/env python3
import os
import sys
import requests
import zipfile

# Dropbox shared folder URL
url = "https://www.dropbox.com/scl/fo/a24ac4749h9qlpa9g0ghu/AJLIxkSrC93v4mtoSU3MUWg?dl=1&rlkey=kmluxze9dha4f78cyua3n0612"
target_zip = "scratch/vitpose_dataset.zip"
extract_dir = "/Users/neilkloot/Code/Batting Sensor Stats/ViTPose/PoseData"

def download_file(url, dest_path):
    print(f"📥 Starting download from: {url}")
    print("This may take a moment while Dropbox zips the folder structure...")
    
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    response = requests.get(url, stream=True, headers=headers)
    
    print("Response Status Code:", response.status_code)
    print("Response Headers:")
    for k, v in list(response.headers.items())[:10]:
        print(f"  {k}: {v}")
        
    response.raise_for_status()
    
    # Read first 500 bytes to check if it's HTML
    preview_chunk = next(response.iter_content(chunk_size=500))
    if b"<!DOCTYPE html>" in preview_chunk or b"<html" in preview_chunk:
        print("\n⚠️ WARNING: The response appears to be HTML instead of a ZIP file!")
        print("Response Preview:")
        print(preview_chunk.decode('utf-8', errors='ignore')[:300])
        raise ValueError("Dropbox returned an HTML page instead of a zip file. This typically means the folder is too large for anonymous direct ZIP download, or a verification screen is shown.")
        
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024 # 1MB
    
    written = len(preview_chunk)
    with open(dest_path, 'wb') as f:
        f.write(preview_chunk)
        for chunk in response.iter_content(chunk_size=block_size):
            if chunk:
                f.write(chunk)
                written += len(chunk)
                if total_size > 0:
                    percent = (written / total_size) * 100
                    print(f"\rProgress: {percent:.1f}% ({written / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB)", end="", flush=True)
                else:
                    print(f"\rProgress: {written / (1024*1024):.1f} MB downloaded...", end="", flush=True)
    print("\n✅ Download finished!")

def extract_zip(zip_path, dest_dir):
    print(f"📦 Extracting {zip_path} to {dest_dir}...")
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dest_dir)
    print("✅ Extraction complete!")

def main():
    os.makedirs("scratch", exist_ok=True)
    try:
        download_file(url, target_zip)
        extract_zip(target_zip, extract_dir)
        
        # Clean up zip
        if os.path.exists(target_zip):
            os.remove(target_zip)
            
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
