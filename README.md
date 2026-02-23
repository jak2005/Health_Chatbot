# HealthLink AI Chatbot

An AI-powered healthcare support system utilizing Retrieval-Augmented Generation (RAG) for accurate, safe, and research-backed health assistance.

---

## 📋 Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Dataset Information](#dataset-information)
- [Tech Stack](#tech-stack)
- [API Keys Setup](#api-keys-setup)

---

## ✨ Features

- 🤖 Intelligent health assistance with RAG-powered responses
- 💬 Web-based interactive chat interface
- 📅 Doctor appointment booking system
- 👨‍⚕️ Doctor dashboard for managing patients
- 🔐 Secure user authentication (JWT + bcrypt)
- 📊 Real-time health tips and recommendations
- 🗄️ Vector database for efficient knowledge retrieval

---

## 💻 System Requirements

| Component | Requirement |
|-----------|-------------|
| **Operating System** | Windows 10/11, macOS, or Linux |
| **Python** | 3.11 or 3.12 (recommended) |
| **RAM** | 4GB minimum, 8GB recommended |
| **Disk Space** | 500MB for dependencies |

### Required Tools

| Tool | Version | Download Link |
|------|---------|---------------|
| Python | 3.11+ | https://www.python.org/downloads/ |
| Git | Latest | https://git-scm.com/downloads |
| pip | Latest | Included with Python |

---

## 🚀 Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Health_Chatbot.git
cd Health_Chatbot
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_google_gemini_api_key
GROQ_API_KEY=your_groq_api_key
SECRET_KEY=your_jwt_secret_key
```

**How to get API keys:**
- **Google Gemini API**: https://aistudio.google.com/app/apikey
- **Groq API**: https://console.groq.com/keys

---

## ▶️ Running the Application

### Option 1: Using the Batch File (Windows)

```bash
start_app.bat
```

### Option 2: Manual Start

**Terminal 1 - Start Backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Start Frontend:**
```bash
streamlit run frontend/app.py
```

### Access the Application

- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📁 Project Structure

```
Health_Chatbot/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── auth.py              # Authentication logic
│   ├── rag_service.py       # RAG pipeline implementation
│   ├── db_manager.py        # Database operations
│   └── persistence.py       # Data persistence layer
├── frontend/
│   ├── app.py               # Streamlit application
│   └── utils.py             # Frontend utilities
├── data/
│   ├── knowledge_base.json  # Medical knowledge base
│   ├── health_tips.json     # Health tips data
│   ├── faqs.json            # FAQ data
│   └── products.json        # Product information
├── requirements.txt         # Python dependencies
├── start_app.bat            # Windows startup script
└── README.md                # This file
```

---

## 📊 Dataset Information

### Knowledge Base (Self-Collected)

The medical knowledge base (`data/knowledge_base.json`) contains curated health information from the following sources:

- **Healthcare.gov API**: Public healthcare marketplace data
- **General health tips**: Curated wellness recommendations
- **FAQ database**: Common health questions and answers

### Data Format

```json
{
  "category": "health_tips",
  "title": "Example Health Tip",
  "content": "Detailed health information...",
  "source": "healthcare.gov"
}
```

> **Note**: If you need to download the dataset separately, it is included in this repository under the `data/` folder.

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | Streamlit | 1.32+ |
| **Backend** | FastAPI | 0.100+ |
| **Database** | SQLite + ChromaDB | Latest |
| **AI Models** | Google Gemini, Groq | Latest |
| **Authentication** | JWT + bcrypt | - |

---

## 🔑 API Keys Setup

### Google Gemini API (Required)

1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key to your `.env` file

### Groq API (Optional - for enhanced responses)

1. Go to https://console.groq.com/keys
2. Create an account or sign in
3. Generate a new API key
4. Copy the key to your `.env` file

---

## 📝 License

This project is developed as a Final Year Project for academic purposes.

---

