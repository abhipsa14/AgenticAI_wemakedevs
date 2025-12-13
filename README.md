# Study Assistant - Multi-Agent System

A **multi-agent AI system** that helps students with:
- 📅 **Study Planning** - Generate personalized day-wise schedules
- ❓ **Doubt Resolution** - Get answers from your own uploaded notes (RAG)
- 📋 **Schedule Management** - Track progress and reschedule missed sessions

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Web Interface                        │
│  (Dashboard | Create Plan | Today's Tasks | Ask Doubt) │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Coordinator Agent    │
              │  (Intent Detection &  │
              │   Request Routing)    │
              └───────────┬───────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ Planner Agent │ │Knowledge Agent│ │Scheduler Agent│
│               │ │               │ │               │
│ Creates study │ │ RAG-based Q&A │ │ Tracks & re-  │
│ schedules     │ │ over notes    │ │ schedules     │
└───────────────┘ └───────────────┘ └───────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   SQLite DB   │ │   ChromaDB    │ │   SQLite DB   │
│   (Plans &    │ │  (Embeddings) │ │  (Sessions)   │
│   Sessions)   │ │               │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
cd AgenticAI_wemakedevs

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
copy .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your_key_here
```

### 3. Run the Application

```bash
# Start the server
uvicorn app.main:app --reload

# Or run directly
python -m app.main
```

### 4. Open in Browser

Navigate to: **http://localhost:8000**

## 📁 Project Structure

```
AgenticAI_wemakedevs/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration settings
│   ├── main.py             # FastAPI application entry
│   │
│   ├── agents/             # AI Agents
│   │   ├── coordinator.py  # Main orchestrator
│   │   ├── planner.py      # Study plan generation
│   │   ├── knowledge.py    # RAG-based Q&A
│   │   ├── scheduler.py    # Schedule management
│   │   └── config/
│   │       └── agents.yaml # Agent configurations
│   │
│   ├── models/             # Database models
│   │   ├── database.py     # SQLModel tables
│   │   └── session.py      # DB session management
│   │
│   ├── routers/            # API endpoints
│   │   ├── plans.py        # Study plan APIs
│   │   ├── schedule.py     # Schedule APIs
│   │   ├── knowledge.py    # Document/Q&A APIs
│   │   └── chat.py         # Chat interface APIs
│   │
│   └── services/           # Business logic
│       ├── pdf_processor.py    # PDF text extraction
│       ├── vector_store.py     # ChromaDB operations
│       └── llm_service.py      # LLM API wrapper
│
├── frontend/
│   └── templates/          # Jinja2 HTML templates
│       ├── base.html       # Base layout
│       ├── index.html      # Dashboard
│       ├── plan.html       # Create plan page
│       ├── schedule.html   # Today's tasks
│       └── knowledge.html  # Notes management
│
├── uploads/                # Uploaded PDFs (auto-created)
├── chroma_db/              # Vector store (auto-created)
├── requirements.txt
├── .env.example
└── README.md
```

## 🤖 Agents

### 1. Coordinator Agent
- Detects user intent from messages
- Routes requests to appropriate specialist agents
- Synthesizes responses for the frontend

### 2. Planner Agent
- Input: Subjects, topics, dates, hours/day
- Output: Day-wise study schedule with time blocks
- Uses LLM to generate intelligent, balanced schedules

### 3. Knowledge Agent (RAG)
- Input: User question + uploaded PDF notes
- Process: Retrieves relevant chunks from ChromaDB
- Output: Answer with source citations

### 4. Scheduler Agent
- Tracks session completion status
- Reschedules missed sessions intelligently
- Provides progress summaries and tips

## 🔌 API Endpoints

### Study Plans
- `POST /api/plans/create` - Create new study plan
- `GET /api/plans/{plan_id}` - Get plan details
- `GET /api/plans/user/{user_id}` - Get user's plans

### Schedule
- `GET /api/schedule/today/{plan_id}` - Today's sessions
- `PUT /api/schedule/session/{id}` - Update session status
- `POST /api/schedule/reschedule/{plan_id}` - Reschedule missed

### Knowledge
- `POST /api/knowledge/upload` - Upload PDF
- `POST /api/knowledge/ask` - Ask question
- `POST /api/knowledge/quiz` - Generate quiz

### Chat
- `POST /api/chat/send` - Send message to assistant
- `GET /api/chat/history/{user_id}` - Get chat history

## 🛠️ Technologies

- **Backend**: FastAPI, Python 3.10+
- **Database**: SQLite + SQLModel
- **Vector Store**: ChromaDB
- **LLM**: OpenAI GPT-4o-mini (configurable)
- **PDF Processing**: PyMuPDF
- **Frontend**: HTML, Tailwind CSS, Vanilla JS

## 📝 Usage Example

### Creating a Study Plan

1. Go to "Create Plan" page
2. Enter plan title and dates
3. Add subjects and topics with difficulty levels
4. Click "Generate Plan" - AI creates your schedule

### Asking Doubts

1. Upload your study notes (PDFs)
2. Click the chat button or go to "My Notes"
3. Type your question
4. Get answers with source citations

### Managing Schedule

1. View today's tasks on dashboard or schedule page
2. Check off completed sessions
3. Skip sessions you couldn't do
4. Use "Reschedule" to automatically adjust plan

## ⚙️ Configuration

Edit `.env` file:

```env
# Required: OpenAI API key for LLM
OPENAI_API_KEY=sk-...

# Optional: Use Groq instead (free tier available)
GROQ_API_KEY=gsk_...

# Database (SQLite by default)
DATABASE_URL=sqlite:///./study_assistant.db

# Debug mode
DEBUG=true
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

## 📄 License

MIT License - feel free to use this for learning and building!

---

Built with ❤️ for students who want to study smarter, not harder.