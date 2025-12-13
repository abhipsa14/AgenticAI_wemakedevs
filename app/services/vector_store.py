"""
Vector store service using ChromaDB for RAG.
"""
import os
from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
from app.config import CHROMA_PERSIST_DIR, OPENAI_API_KEY


class VectorStore:
    """Vector store for document embeddings using ChromaDB."""
    
    def __init__(self, persist_dir: str = CHROMA_PERSIST_DIR):
        os.makedirs(persist_dir, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self._setup_embedding_function()
    
    def _setup_embedding_function(self):
        """Configure the embedding function."""
        if OPENAI_API_KEY:
            try:
                from chromadb.utils import embedding_functions
                self.embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=OPENAI_API_KEY,
                    model_name="text-embedding-3-small"
                )
            except Exception:
                self.embedding_fn = chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
        else:
            self.embedding_fn = chromadb.utils.embedding_functions.DefaultEmbeddingFunction()
    
    def get_or_create_collection(self, user_id: int, collection_name: str = "study_notes"):
        """Get or create a collection for a user's documents."""
        full_name = f"user_{user_id}_{collection_name}"
        return self.client.get_or_create_collection(
            name=full_name,
            embedding_function=self.embedding_fn,
            metadata={"user_id": str(user_id)}
        )
    
    def add_document_chunks(
        self, user_id: int, document_id: int, chunks: List[Dict],
        filename: str, subject: Optional[str] = None
    ) -> int:
        """Add document chunks to the vector store."""
        collection = self.get_or_create_collection(user_id)
        
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            chunk_id = f"doc_{document_id}_chunk_{chunk['chunk_index']}"
            ids.append(chunk_id)
            documents.append(chunk['text'])
            metadatas.append({
                'document_id': str(document_id),
                'filename': filename,
                'subject': subject or 'general',
                'chunk_index': chunk['chunk_index']
            })
        
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return len(ids)
    
    def search(
        self, user_id: int, query: str, n_results: int = 5,
        subject_filter: Optional[str] = None
    ) -> List[Dict]:
        """Search for relevant document chunks."""
        collection = self.get_or_create_collection(user_id)
        
        where_filter = {"subject": subject_filter} if subject_filter else None
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception:
            return []
        
        formatted_results = []
        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    'text': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0,
                    'relevance_score': 1 - (results['distances'][0][i] if results['distances'] else 0)
                })
        
        return formatted_results
    
    def delete_document(self, user_id: int, document_id: int) -> bool:
        """Delete all chunks for a document."""
        collection = self.get_or_create_collection(user_id)
        
        try:
            results = collection.get(where={"document_id": str(document_id)})
            if results['ids']:
                collection.delete(ids=results['ids'])
            return True
        except Exception:
            return False
    
    def get_collection_stats(self, user_id: int) -> Dict:
        """Get statistics about a user's document collection."""
        collection = self.get_or_create_collection(user_id)
        try:
            return {'total_chunks': collection.count()}
        except Exception:
            return {'total_chunks': 0}


# Global instance
vector_store = VectorStore()
