# 🎓 CampusMate AI
> **The Premium, Glassmorphic AI Career & Learning Operating System for Students.**

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new?template=https://github.com/251801390006-blip/campusmate-ai)
[![Python Version](https://img.shields.io/badge/python-3.12-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Flask Version](https://img.shields.io/badge/Flask-3.0.3-009688?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/251801390006-blip/campusmate-ai?style=flat-square)](https://github.com/251801390006-blip/campusmate-ai/stargazers)
---

## 🏆 Microsoft Hackathon Submission
Welcome Judges! CampusMate AI is fully ready for your review. Please see our official evaluation resources:
- [Architecture Diagram](./ARCHITECTURE.md)
- [System Workflow](./WORKFLOW.md)
- [Demo Video Checklist](./DEMO_CHECKLIST.md)
- [Judge Evaluation Rubric](./JUDGE_RUBRIC.md)

---

## 🏗️ Architecture & Data Flow

CampusMate AI is built on a robust, state-of-the-art Python stack using a Flask backend, SQLAlchemy database layers, and HTML5/Vanilla CSS frontend modules. It features contextual generative AI workflows using the official Google GenAI SDK.

```
                      +------------------------------------------+
                      |           Student Client Browser         |
                      |   - HSL tailored glassmorphic styles     |
                      |   - Interactive visual roadmap canvas    |
                      |   - Single-page A4 PDF rendering         |
                      +-------------------+----------------------+
                                          |
                                          v  [HTTPS requests]
                      +-------------------+----------------------+
                      |             Flask Web Server             |
                      |   - Blueprints routing & API endpoints   |
                      |   - Flask-Login secure sessions          |
                      |   - CSRF & WTF forms validation schemas  |
                      +---+----------------------------------+---+
                          |                                  |
                          v  [SQLAlchemy ORM]                v  [GenAI SDK]
            +-------------+-------------+      +-------------+-------------+
            |      SQLite / Postgres    |      |     Google Gemini API     |
            |      - User & Admin logs  |      |     - gemini-2.5-flash    |
            |      - Draft resume states|      |     - Live stream responses|
            |      - Roadmap progress   |      |     - Heuristic audit maps|
            +---------------------------+      +---------------------------+
```

---

## 📂 Repository File Structure

```
├── .github/
│   └── workflows/
│       └── verify.yml       # Automated CI workflow compilation checking
├── app/                     # Main Flask Application
│   ├── __init__.py          # App initialization, SQLAlchemy config, Flask-Login setup
│   ├── forms.py             # Form validation schemas (Login, Register, Settings)
│   ├── models.py            # Relational database models (User, Resume, RoadmapProgress, etc.)
│   ├── routes/              # Blueprints containing views and API controllers
│   │   ├── admin.py         # Admin Dashboard metrics, logs, user control, announcements
│   │   ├── auth.py          # Secure student authentication logic (onboarding)
│   │   ├── dashboard.py     # Main student dashboard workspace and activity tracker
│   │   ├── features.py      # Core AI engines (Roadmaps, Resume Analyzer, Interview Prep, etc.)
│   │   └── feedback.py      # User feedback log dispatchers
│   ├── static/              # Static assets directory
│   │   ├── css/
│   │   │   └── style.css    # Premium CSS design variables (Light & Day/Dark themes)
│   │   └── js/
│   │       ├── mentor.js    # Floating AI Mentor chat drawer stream controller
│   │       └── roadmaps.js  # Roadmap canvas rendering with interactive nodes
│   └── templates/           # Server-side HTML layout templates (Jinja2)
│       ├── base.html        # App-wide layout base
│       ├── dashboard_base.html # Student sidebar dashboard base
│       └── ...              # Feature-specific pages (dashboard.html, roadmaps.html, etc.)
├── Dockerfile               # Production container build recipe
├── railway.json             # Railway app configurations and bindings
├── main.py                  # App entrypoint execution script
├── requirements.txt         # Locked project packages dependencies list
├── database.db              # SQLite development database
└── LICENSE                  # Open-source MIT License
```

---

## 🛠️ Feature Breakdown

### 1. 🗺️ Non-Linear Visual Roadmaps
- **200+ Career Checkpoints**: Interactive node diagrams for **8 target fields** (Cybersecurity, AI Engineering, Machine Learning, Data Science, Cloud Computing, DevOps, Full Stack Web, and Mobile Development).
- **Navigation Console**: Fluid canvas controls featuring Zoom In, Zoom Out, Reset, Up, Down, Left, and Right navigations.
- **Resource Routing**: Curated learning references mapping directly to industry platforms (Google, GeeksForGeeks, MDN).
- **Day / Dark Mode**: Integrated workspace toggles adapting UI elements to HSL tailored color schemes dynamically.

### 2. 📝 Single-Page ATS Resume Builder
- **Strict Single-Page PDF Layout**: Strict `.pdf-export-mode` styling compressing fonts, margins, and section spacing to guarantee the output prints on exactly a single A4 page (`297mm`).
- **Clean Job-Focused Editor**: Strictly focused on essential tech resume sections: **Education**, **Technical Skills**, **Experience**, **Projects**, and **Certifications**.
- **Interactive Parsing & Audit Zone**: Drag-and-drop zone extracting PDF/DOCX content to analyze with a real-time keyword scanner and Google XYZ formula validator.
- **Enhanced Downloads**: Fast, responsive download controller scaling canvas resolution (`2.5`) for sharp vector texts, preventing concurrent triggers, and rendering loader indicators during PDF generation.

### 3. 💬 Floating AI Career Mentor
- **Typewriter Streaming**: Simulates real-time word-by-word response formulation with elegant glassmorphic drawer elements.
- **統計 Performance Memory Ribbon**: Displays active student statistics (track, XP achievements, resume score) within the chat console to maintain continuous advisor context.
- **Context Suggestion Chips**: Auto-generated guidance query chips updating contextually based on user messages.

### 4. 🎙️ AI Interview Simulator
- **Live Text-to-Speech (TTS)**: Practicing typical tech screening questions with speech output support and progress evaluations.

### 5. 🏗️ AI Project Architect
- **Component Schemas**: Generates directory tree blueprints and database structures for target projects.

### 6. 💼 Internship Command Center
- **Rate Eligibility**: Automatically extracts user skills, filters internships populated by the Admin dashboard, maps matched tags, and ratings eligibility.

---

## 💻 Local Quickstart

### Prerequisites
*   Python 3.11 or higher
*   Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/251801390006-blip/campusmate-ai.git
   cd campusmate-ai
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv .venv
   
   # Windows (PowerShell/CMD)
   .venv\Scripts\activate
   
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run development server:**
   ```bash
   python main.py
   ```
   Open **`http://127.0.0.1:5000`** in your browser to view the application.

---

## 🚀 Production Deployment

### Live Deployment via Railway
1. Click the **Deploy on Railway** button at the top of the README.
2. Grant Railway permissions to build from this fork.
3. Inject the environment variable **`GEMINI_API_KEY`** using your API key from Google AI Studio.
4. Railway will automatically build the container via the `Dockerfile` and publish an HTTPS endpoint.
