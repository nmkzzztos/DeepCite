--- 
id: "getting-started"
title: "Getting Started"
sidebar_position: 1
---

# Getting Started

This guide will help you set up the DeepCite development environment.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose (optional, for containerized setup)

## Quick Start with Docker Compose

The easiest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone <repository-url>
cd deepcite

# Start all services (backend, frontend)
docker-compose up -d

# Check service health
docker-compose ps

# View logs
docker-compose logs -f backend
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## Manual Setup

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
# Copy the example (if available) or create your own
cp .env.example .env  # Optional, or create manually
# Edit .env with your configuration (see Environment Variables section below)

# Initialize database
python startup.py

# Run the application
python app.py
```

The backend will be available at `http://localhost:5000`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

```env
# Database Configuration
# For SQLite (default, development):
DATABASE_URL=sqlite:///instance/deepcite.db

# For PostgreSQL (production):
# DATABASE_URL=postgresql://user:password@localhost:5432/deepcite

# Flask Configuration
SECRET_KEY=your-secret-key-here-change-in-production
FLASK_ENV=development
UPLOAD_FOLDER=./uploads
MAX_CONTENT_LENGTH=16777216

# Vector Database (Chroma)
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_TELEMETRY_ENABLED=false

# AI Model Providers (Optional)
# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key

# Perplexity
PERPLEXITY_API_KEY=your-perplexity-api-key

# OpenRouter
OPENROUTER_API_KEY=your-openrouter-api-key

# PDF Parsing Configuration
GROBID_URL=http://localhost:8070
ENABLE_GROBID=true
ENABLE_TOC_PARSING=true
DEFAULT_PARSING_STRATEGY=auto

# Local Models (if using Ollama or llama.cpp)
ENABLE_LOCAL_MODELS=false
OLLAMA_ENDPOINT=http://localhost:11434
LLAMACPP_ENDPOINT=http://localhost:8080
```

## Development Workflow

### Option 1: Manual Setup (Current Recommended)
1. **Terminal 1 - Backend**:
   ```bash
   cd backend
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   python app.py
   ```

2. **Terminal 2 - Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

### Option 2: Docker Compose (When Fully Configured)
```bash
docker-compose up -d
```

## API Documentation

Once the backend is running, test the API:

```bash
# Health check
curl http://localhost:5000/api/v1/health

# List documents
curl http://localhost:5000/api/v1/documents

# List workspaces
curl http://localhost:5000/api/v1/workspaces
```

## Project Structure

- `backend/` - Flask REST API server
- `frontend/` - Vue.js 3 client application
- `uploads/` - Uploaded PDF files storage
- `docker-compose.yml` - Multi-service orchestration config

## Troubleshooting

### Backend Issues

**Database Connection Errors**
- Verify `DATABASE_URL` in `.env` is correct
- For SQLite: ensure `instance/` directory exists and is writable
- For PostgreSQL: ensure PostgreSQL is running and accessible

**Port Already in Use**
- Backend defaults to port 5000
- Check if port is in use: `lsof -i :5000` (macOS/Linux)
- Or modify `app.py` to use a different port

**Missing Dependencies**
- Run: `pip install -r requirements.txt`
- Ensure you're in the correct virtual environment

### Frontend Issues

**Node Module Issues**
- Clear and reinstall: `rm -rf node_modules package-lock.json && npm install`
- Check Node.js version: `node --version` (should be 18+)

**Port 3000 Already in Use**
- Frontend uses Vite dev server on port 3000
- Change in `vite.config.ts` if needed

**API Connection Failed**
- Ensure backend is running on `http://localhost:5000`
- Check browser console for errors
- Verify CORS is enabled in backend

### Vector Database

**Chroma Connection Issues**
- Default uses local SQLite-backed Chroma
- Data stored in `chroma_db/` directory
- If issues persist, try clearing: `rm -rf chroma_db/`

## Next Steps

After successful setup:
1. Access the application at http://localhost:3000
2. Create a workspace
3. Upload PDF documents through the web interface
4. Start chatting with your documents using RAG

## For Production Deployment

- Use PostgreSQL instead of SQLite
- Set `SECRET_KEY` to a strong random value
- Use environment-specific `.env` files
- Set `FLASK_ENV=production` and `DEBUG=false`
- Consider using Gunicorn for serving the Flask app
- Set up a reverse proxy (nginx) for the frontend build