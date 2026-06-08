# CampusMate AI 2.0
> **The Premium AI Career & Learning Operating System for Students.**

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new?template=https://github.com/251801390006-blip/campusmate-ai)

[![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/251801390006-blip/campusmate-ai?style=flat-square)](https://github.com/251801390006-blip/campusmate-ai/stargazers)

CampusMate AI is an advanced educational SaaS platform designed to accelerate student learning and career goals. It functions in two modes: a client-side **Standalone Sandbox Mode** (using `localStorage` for offline use) and a **Connected Server Mode** backed by a FastAPI/SQLite service.

---

## 🏗️ System Architecture & Data Flow

```
                      +---------------------------------------+
                      |         Student Browser UI            |
                      |   (HTML5 / Outfit Font / CSS Vars)     |
                      +-------------------+-------------------+
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v [Offline Fallback]                      v [API Requests]
        +------------+-------------+             +-------------+-------------+
        |  Browser LocalStorage    |             |    FastAPI App Server     |
        |  - Streak & XP meters    |             |    - Auth & JWT tokens    |
        |  - 8-Track Sandbox Maps  |             |    - Upload parser logic  |
        |  - Emulated ATS scores   |             |    - SQLite Persistence   |
        +--------------------------+             +-------------+-------------+
                                                               |
                                                               v [LLM API call]
                                                 +-------------+-------------+
                                                 |      Gemini API Gateway   |
                                                 |      (gemini-2.5-flash)   |
                                                 +---------------------------+
```

---

## 📂 Repository File Structure

```
├── .github/workflows/
│   └── verify.yml           # Automated CI syntax compiler checks
├── static/                  # Frontend single-page app (SPA) assets
│   ├── css/
│   │   └── style.css        # Light-mode first glassmorphic variables & rules
│   ├── js/
│   │   ├── api.js           # REST client wrapper endpoints
│   │   └── app.js           # Client-side router, sandbox database seeds
│   └── index.html           # 9-section landing page and student dashboard UI
├── Dockerfile               # Dynamic port binding deployment configuration
├── railway.json             # Service instructions for Railway builders
├── requirements.txt         # Declared python dependencies
├── models.py                # SQLModel relational database definitions
├── database.py              # SQLite engine connection setup
├── main.py                  # API endpoints, JWT, and Gemini client wrappers
├── LICENSE                  # MIT open-source license
└── README.md                # Enterprise-grade project documentation
```

---

## 🛠️ Key Product Features

### 1. AI Mentor 2.0 (Deep Dialog System)
*   **Typewriter Animation**: Displays response segments incrementally to match server-streaming styles.
*   **Active Memory Ribbon**: Renders active student statistics (career path, XP, resume grade) directly inside the chatbot interface.
*   **Suggestion Chips**: Clickable prompt bubbles that refresh contextually to trigger technical guidelines immediately.
*   **Chat History Persistence**: Logs conversations to local storage, maintaining context even after view transitions.

### 2. Double-Mode ATS Resume Builder 2.0
*   **Manual Form Sync**: Dynamic input forms updating Ivory, Modern Cyan, or Slate Glass print layouts.
*   **Drag-and-Drop Parsing**: Interactive file zone supporting PDF/DOCX uploads. Analyzes files and extracts content vectors automatically.
*   **Checklist Audit**: Generates missing keywords guidelines and Google XYZ formula suggestions.

### 3. Expandable Roadmap Engine 2.0
*   Supports **8 custom target tracks**: Cyber Security, AI Engineering, Machine Learning, Data Science, Cloud Computing, DevOps, Full Stack Web, and Mobile Development.
*   Seeds non-linear checkposts populated with duration targets, task checklists, and matched certifications.

---

## 🚀 Deployment Guide

### One-Click Deployment via Railway

To deploy this project to your own live URL instantly:

1.  Click the **Deploy on Railway** button at the top of this document.
2.  Grant Railway access to your GitHub account.
3.  Add the optional **`GEMINI_API_KEY`** environment variable to enable live AI responses.
4.  Railway will configure everything, build the container, and assign a public HTTPS domain.

---

## 💻 Local Quickstart

### Prerequisites
*   Python 3.11 or higher
*   Git

### Installation
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/251801390006-blip/campusmate-ai.git
    cd campusmate-ai
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install Required Libraries:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Launch Server:**
    ```bash
    uvicorn main:app --host 127.0.0.1 --port 8000
    ```
    Visit **`http://127.0.0.1:8000`** in your browser to view the application.

5.  **Offline Sandbox Mode:**
    If you do not want to run a local server, simply double-click **`static/index.html`** in your file manager to run 100% locally inside your browser!
