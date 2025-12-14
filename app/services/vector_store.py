"""
Vector store service using in-memory storage with OpenAI embeddings.
Optimized for serverless deployment (Vercel).
"""
import os
import json
from typing import List, Dict, Optional
from pathlib import Path
from openai import OpenAI
from app.config import CHROMA_PERSIST_DIR, OPENAI_API_KEY


class VectorStore:
    """Lightweight vector store using OpenAI embeddings and in-memory/file storage."""
    
    def __init__(self, persist_dir: str = CHROMA_PERSIST_DIR):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collections: Dict[str, Dict] = {}
        self.client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self._load_collections()
    
    def _load_collections(self):
        """Load existing collections from disk."""
        try:
            index_file = self.persist_dir / "collections_index.json"
            if index_file.exists():
                with open(index_file, 'r') as f:
                    self.collections = json.load(f)
        except Exception:
            self.collections = {}
    
    def _save_collections(self):
        """Save collections to disk."""
        try:
            index_file = self.persist_dir / "collections_index.json"
            with open(index_file, 'w') as f:
                json.dump(self.collections, f)
        except Exception:
            pass
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI."""
        if not self.client:
            # Fallback: simple hash-based pseudo-embedding for testing
            import hashlib
            hash_val = hashlib.md5(text.encode()).hexdigest()
            return [int(hash_val[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
        
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]  # Limit text length
            )
            return response.data[0].embedding
        except Exception:
            # Fallback on error
            import hashlib
            hash_val = hashlib.md5(text.encode()).hexdigest()
            return [int(hash_val[i:i+2], 16) / 255.0 for i in range(0, 32, 2)]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
    
    def get_or_create_collection(self, user_id: int, collection_name: str = "study_notes"):
        """Get or create a collection for a user's documents."""
        full_name = f"user_{user_id}_{collection_name}"
        if full_name not in self.collections:
            self.collections[full_name] = {
                "name": full_name,
                "user_id": str(user_id),
                "documents": [],
                "embeddings": [],
                "metadatas": [],
                "ids": []
            }
            self._save_collections()
        return full_name
    
    def add_document_chunks(
        self, user_id: int, document_id: int, chunks: List[Dict],
        filename: str, subject: Optional[str] = None
    ) -> int:
        """Add document chunks to the vector store."""
        collection_name = self.get_or_create_collection(user_id)
        collection = self.collections[collection_name]
        
        for chunk in chunks:
            chunk_id = f"doc_{document_id}_chunk_{chunk['chunk_index']}"
            
            # Skip if already exists
            if chunk_id in collection["ids"]:
                continue
            
            text = chunk['text']
            embedding = self._get_embedding(text)
            
            collection["ids"].append(chunk_id)
            collection["documents"].append(text)
            collection["embeddings"].append(embedding)
            collection["metadatas"].append({
                'document_id': str(document_id),
                'filename': filename,
                'subject': subject or 'general',
                'chunk_index': chunk['chunk_index']
            })
        
        self._save_collections()
        return len(chunks)
    
    def search(
        self, user_id: int, query: str, n_results: int = 5,
        subject_filter: Optional[str] = None
    ) -> List[Dict]:
        """Search for relevant document chunks."""
        collection_name = self.get_or_create_collection(user_id)
        collection = self.collections[collection_name]
        
        if not collection["documents"]:
            return []
        
        try:
            query_embedding = self._get_embedding(query)
            
            # Calculate similarities
            similarities = []
            for i, doc_embedding in enumerate(collection["embeddings"]):
                metadata = collection["metadatas"][i]
                
                # Apply subject filter if provided
                if subject_filter and metadata.get('subject') != subject_filter:
                    continue
                
                similarity = self._cosine_similarity(query_embedding, doc_embedding)
                similarities.append({
                    'index': i,
                    'similarity': similarity,
                    'text': collection["documents"][i],
                    'metadata': metadata
                })
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Return top n results
            formatted_results = []
            for item in similarities[:n_results]:
                formatted_results.append({
                    'text': item['text'],
                    'metadata': item['metadata'],
                    'distance': 1 - item['similarity'],
                    'relevance_score': item['similarity']
                })
            
            return formatted_results
        except Exception:
            return []
    
    def delete_document(self, user_id: int, document_id: int) -> bool:
        """Delete all chunks for a document."""
        collection_name = self.get_or_create_collection(user_id)
        collection = self.collections[collection_name]
        
        try:
            # Find indices to delete
            indices_to_delete = []
            for i, metadata in enumerate(collection["metadatas"]):
                if metadata.get("document_id") == str(document_id):
                    indices_to_delete.append(i)
            
            # Delete in reverse order to maintain indices
            for i in reversed(indices_to_delete):
                collection["ids"].pop(i)
                collection["documents"].pop(i)
                collection["embeddings"].pop(i)
                collection["metadatas"].pop(i)
            
            self._save_collections()
            return True
        except Exception:
            return False
    
    def get_collection_stats(self, user_id: int) -> Dict:
        """Get statistics about a user's document collection."""
        collection_name = self.get_or_create_collection(user_id)
        collection = self.collections[collection_name]
        try:
            return {'total_chunks': len(collection["documents"])}
        except Exception:
            return {'total_chunks': 0}


# Global instance
vector_store = VectorStore()
