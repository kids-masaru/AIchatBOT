"""
Knowledge Ingestion Script (The Librarian)
Reads files from configured Google Drive folders and saves them to Pinecone.
"""
import sys
import os

# Add parent dir to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sheets_config import load_config
from tools.google_ops import read_drive_file, search_drive
from utils.vector_store import save_knowledge_vector

def chunk_text(text, chunk_size=1000, overlap=200):
    """Split text into chunks with overlap"""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
        
    return chunks

def run_ingestion():
    print("Starting Knowledge Ingestion...", file=sys.stderr)
    
    # 1. Load Config
    config = load_config()
    sources = config.get('knowledge_sources', [])
    
    if not sources:
        print("No knowledge sources configured.", file=sys.stderr)
        return
    
    total_docs = 0
    total_chunks = 0
    
    # 2. Iterate Sources
    for source in sources:
        folder_id = source.get('id')
        folder_name = source.get('name', 'Unknown')
        
        if not folder_id: continue
        
        print(f"Scanning folder: {folder_name} ({folder_id})", file=sys.stderr)
        
        # 3. List Files in Folder (Recursive)
        from googleapiclient.discovery import build
        from utils.auth import get_google_credentials
        
        creds = get_google_credentials()
        drive_service = build('drive', 'v3', credentials=creds)
        
        def list_files_recursive(folder_id, parent_name=""):
            all_files = []
            page_token = None
            
            while True:
                # Search for files AND folders
                term = f"'{folder_id}' in parents and trashed=false"
                results = drive_service.files().list(
                    q=term,
                    fields="nextPageToken, files(id, name, mimeType)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                
                for item in items:
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        # Found a subfolder, recurse
                        sub_name = f"{parent_name}/{item['name']}" if parent_name else item['name']
                        print(f"  Scanning subfolder: {sub_name}", file=sys.stderr)
                        all_files.extend(list_files_recursive(item['id'], sub_name))
                    elif item['mimeType'] in ['application/pdf', 'application/vnd.google-apps.document', 'text/plain']:
                        # Found a valid document
                        item['path_name'] = f"{parent_name}/{item['name']}" if parent_name else item['name']
                        all_files.append(item)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            return all_files

        files = list_files_recursive(folder_id)
        print(f"Found {len(files)} documents in potential subfolders.", file=sys.stderr)

        
        # 4. Process Files
        for file in files:
            file_id = file['id']
            filename = file['name']
            print(f"  Reading: {filename}...", file=sys.stderr)
            
            # Read content
            res = read_drive_file(file_id)
            if not res.get('success'):
                print(f"    Failed to read: {res.get('error')}", file=sys.stderr)
                continue
                
            content = res.get('content', '')
            if not content:
                print("    Empty content.", file=sys.stderr)
                continue
                
            # Chunking
            chunks = chunk_text(content)
            print(f"    Chunked into {len(chunks)} parts.", file=sys.stderr)
            
            # Save vectors
            for i, chunk in enumerate(chunks):
                doc_id = f"doc:{file_id}:chunk:{i}"
                metadata = {
                    "source": filename,
                    "folder": folder_name,
                    "file_id": file_id,
                    "chunk_index": i,
                    "text": chunk, # Store text for retrieval
                    "type": "knowledge"
                }
                
                success = save_knowledge_vector(doc_id, chunk, metadata)
                if not success:
                    print(f"    Failed to save chunk {i}", file=sys.stderr)
            
            total_docs += 1
            total_chunks += len(chunks)

    print(f"Ingestion Complete. Processed {total_docs} docs, {total_chunks} chunks.", file=sys.stderr)

if __name__ == "__main__":
    run_ingestion()
