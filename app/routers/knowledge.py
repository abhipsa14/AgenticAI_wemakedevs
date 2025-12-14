"""
Knowledge/Document management API routes.
"""
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models.session import get_session
from app.models.database import User, KnowledgeDocument
from app.services.pdf_processor import save_uploaded_file, process_pdf
from app.services.vector_store import vector_store
from app.agents.knowledge import knowledge_agent

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class QuestionRequest(BaseModel):
    question: str
    subject: Optional[str] = None


class ExplainRequest(BaseModel):
    topic: str
    depth: str = "detailed"


class QuizRequest(BaseModel):
    topic: str
    num_questions: int = 5


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    subject: str = Form(default="general"),
    db: Session = Depends(get_session)
):
    """Upload a PDF document for the knowledge base."""
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Get or create user
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        user = User(email="demo@example.com", name="Demo User")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Save file
    content = await file.read()
    file_path = save_uploaded_file(content, file.filename, user.id)
    
    # Process PDF
    try:
        processed = process_pdf(file_path)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")
    
    # Save document record
    doc = KnowledgeDocument(
        user_id=user.id,
        filename=file.filename,
        file_path=file_path,
        subject=subject,
        total_chunks=processed['metadata']['total_chunks']
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Add to vector store
    num_chunks = vector_store.add_document_chunks(
        user_id=user.id,
        document_id=doc.id,
        chunks=processed['chunks'],
        filename=file.filename,
        subject=subject
    )
    
    return {
        "success": True,
        "document_id": doc.id,
        "filename": file.filename,
        "subject": subject,
        "chunks_created": num_chunks,
        "total_chars": processed['metadata']['total_chars']
    }


@router.get("/documents")
async def list_documents(db: Session = Depends(get_session)):
    """List all uploaded documents."""
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        return {"documents": []}
    
    docs = db.exec(select(KnowledgeDocument).where(KnowledgeDocument.user_id == user.id)).all()
    
    return {
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "subject": d.subject,
                "uploaded_at": d.uploaded_at.isoformat(),
                "chunks": d.chunk_count
            }
            for d in docs
        ]
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, db: Session = Depends(get_session)):
    """Delete a document from the knowledge base."""
    
    doc = db.get(KnowledgeDocument, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from vector store
    vector_store.delete_document(doc.user_id, doc_id)
    
    # Delete file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    
    # Delete record
    db.delete(doc)
    db.commit()
    
    return {"success": True, "message": "Document deleted"}


@router.post("/ask")
async def ask_question(
    request: QuestionRequest,
    db: Session = Depends(get_session)
):
    """Ask a question using RAG from uploaded documents."""
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        return {
            "success": False,
            "error": "No user found. Please upload some documents first."
        }
    
    result = knowledge_agent.answer_question(
        user_id=user.id,
        question=request.question,
        subject_filter=request.subject
    )
    
    return result


@router.post("/explain")
async def explain_topic(
    request: ExplainRequest,
    db: Session = Depends(get_session)
):
    """Get an explanation of a topic using uploaded notes."""
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        user = User(email="demo@example.com", name="Demo User")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    result = knowledge_agent.explain_topic(
        user_id=user.id,
        topic=request.topic,
        depth=request.depth
    )
    
    return result


@router.post("/quiz")
async def generate_quiz(
    request: QuizRequest,
    db: Session = Depends(get_session)
):
    """Generate a quiz on a topic."""
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        user = User(email="demo@example.com", name="Demo User")
        db.add(user)
        db.commit()
        db.refresh(user)
    
    result = knowledge_agent.generate_quiz(
        user_id=user.id,
        topic=request.topic,
        num_questions=request.num_questions
    )
    
    return result


@router.get("/stats")
async def get_knowledge_stats(db: Session = Depends(get_session)):
    """Get statistics about the knowledge base."""
    
    user = db.exec(select(User).where(User.email == "demo@example.com")).first()
    if not user:
        return {"total_documents": 0, "total_chunks": 0, "subjects": []}
    
    docs = db.exec(select(KnowledgeDocument).where(KnowledgeDocument.user_id == user.id)).all()
    
    subjects = list(set(d.subject for d in docs))
    
    vector_stats = vector_store.get_collection_stats(user.id)
    
    return {
        "total_documents": len(docs),
        "total_chunks": vector_stats.get('total_chunks', 0),
        "subjects": subjects
    }
