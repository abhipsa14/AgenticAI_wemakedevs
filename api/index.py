"""
Vercel serverless function entry point.
"""
from app.main import app

# Vercel expects the app to be named 'app' or 'handler'
# FastAPI app is already named 'app', so this works directly
