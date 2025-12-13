"""
PDF processing service for extracting text from uploaded documents.
"""
import os
import hashlib
from typing import List, Dict
from pypdf import PdfReader
from app.config import UPLOAD_DIR


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    reader = PdfReader(pdf_path)
    text = ""
    for page_num, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        text += f"\n--- Page {page_num + 1} ---\n{page_text}"
    return text.strip()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
    """Split text into overlapping chunks for embedding."""
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < text_length:
            for sep in ['. ', '.\n', '\n\n']:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1:
                    end = start + last_sep + len(sep)
                    break
        
        chunk_text_content = text[start:end].strip()
        if chunk_text_content:
            chunks.append({
                'text': chunk_text_content,
                'start_char': start,
                'end_char': end,
                'chunk_index': len(chunks)
            })
        
        start = end - overlap if end < text_length else text_length
    
    return chunks


def process_pdf(pdf_path: str, chunk_size: int = 1000, overlap: int = 200) -> Dict:
    """Process a PDF file: extract text and create chunks."""
    full_text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(full_text, chunk_size, overlap)
    
    return {
        'full_text': full_text,
        'chunks': chunks,
        'metadata': {
            'file_path': pdf_path,
            'file_name': os.path.basename(pdf_path),
            'total_chars': len(full_text),
            'total_chunks': len(chunks)
        }
    }


def save_uploaded_file(file_content: bytes, filename: str, user_id: int) -> str:
    """Save an uploaded file to the uploads directory."""
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    
    file_hash = hashlib.md5(file_content).hexdigest()[:8]
    safe_filename = f"{file_hash}_{filename}"
    file_path = user_dir / safe_filename
    
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    return str(file_path)
