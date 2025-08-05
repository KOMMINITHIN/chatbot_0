# University AI Chatbot

A local AI-powered chatbot system for universities with RAG capabilities and user management.

## Features
- Local AI chat using Ollama
- Document-based knowledge base (RAG)
- User authentication (Admin, Faculty, Student roles)
- Document upload and processing
- Offline-first architecture

## Setup Instructions

1. Install Python 3.8+ and pip

2. Install Ollama:
   - Windows: Download from https://ollama.ai/download
   - Run: `ollama pull qwen`

3. Create and activate virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Initialize the database:
```bash
python init_db.py
```

6. Run the application:
```bash
python app.py
```

7. Access the application at http://localhost:5000

## Project Structure
- `app.py`: Main application file
- `models.py`: Database models
- `rag.py`: RAG implementation
- `static/`: CSS and JavaScript files
- `templates/`: HTML templates
- `uploads/`: Document storage
- `vector_store/`: FAISS vector database

## User Roles
- Admin: Full system access
- Faculty: Can upload documents and manage students
- Student: Can chat with AI and access documents 