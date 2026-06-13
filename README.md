<div align="center">
  <img src="https://img.shields.io/badge/CampusMate-AI-6366f1?style=for-the-badge&logo=openai&logoColor=white" alt="CampusMate AI Logo" />
  <h1>🎓 CampusMate AI</h1>
  <p><strong>The Premium, Glassmorphic AI Career & Learning Operating System for Students.</strong></p>

  [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new?template=https://github.com/251801390006-blip/campusmate-ai)
  [![Python Version](https://img.shields.io/badge/python-3.12-blue?style=flat-square&logo=python)](https://www.python.org/)
  [![Flask Version](https://img.shields.io/badge/Flask-3.0.3-009688?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
  [![Security Status](https://img.shields.io/badge/Security-100%25_Passed-brightgreen?style=flat-square&logo=shield)](https://github.com/251801390006-blip/campusmate-ai)
  [![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
</div>

---

## 🏆 Microsoft Hackathon Submission
Welcome Judges! CampusMate AI is fully prepared for the **Microsoft Agents League** review. We have officially passed our 12-Phase DevSecOps Security Audit.

Please review our official evaluation resources:
- 🏗️ **[Architecture Diagram](./ARCHITECTURE.md)**
- 🔄 **[System Workflow](./WORKFLOW.md)**
- 🎥 **[Demo Video Checklist](./DEMO_CHECKLIST.md)**
- 📊 **[Judge Evaluation Rubric](./JUDGE_RUBRIC.md)**

---

## ✨ Key Features

CampusMate AI provides a fully immersive, personalized career acceleration environment:

### 🗺️ Non-Linear Visual Roadmaps
- **200+ Career Checkpoints**: Interactive node diagrams for **8 target fields** (Cybersecurity, AI Engineering, Machine Learning, Data Science, Cloud Computing, DevOps, Full Stack Web, and Mobile Development).
- **Navigation Console**: Fluid canvas controls featuring Zoom, Pan, Reset, and directional navigations.
- **Resource Routing**: Curated learning references mapping directly to industry-standard platforms (Google, MDN, GeeksForGeeks).

### 📝 Single-Page ATS Resume Builder
- **Strict Layout Constraints**: Advanced `.pdf-export-mode` styling compresses fonts, margins, and section spacing to guarantee output prints perfectly on exactly a single A4 page.
- **Clean Job-Focused Editor**: Strictly focused on essential tech sections: Education, Technical Skills, Experience, Projects, and Certifications.
- **Interactive Parsing & Audit**: Drag-and-drop zone extracting PDF/DOCX content to analyze with a real-time keyword scanner and Google's XYZ formula validator.

### 💬 Floating AI Career Mentor
- **Typewriter Streaming**: Simulates real-time word-by-word response formulation.
- **Contextual Memory**: Displays active student statistics (track, XP achievements, resume score) within the chat console to maintain continuous advisor context.
- **Smart Suggestions**: Auto-generated guidance query chips updating dynamically based on conversation flow.

### 🎙️ AI Interview Simulator & 💼 Internship Center
- **Live TTS Simulation**: Practice typical tech screening questions with speech output support and progress evaluations.
- **Intelligent Internship Matching**: Automatically extracts user skills and filters available opportunities, calculating personalized eligibility ratings.

---

## 🏗️ Architecture & Data Flow

CampusMate AI is built on a robust Python stack using a **Flask WSGI** backend, **SQLAlchemy** database layers, and responsive **HTML5/Vanilla CSS** frontend modules with glassmorphic aesthetics. It features contextual generative AI workflows powered by the official **Google GenAI SDK** and **Groq LLaMA**.

```text
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
            |      SQLite / Postgres    |      |     AI Model Providers    |
            |      - User & Admin logs  |      |     - Gemini 2.5 Flash    |
            |      - Draft resume states|      |     - LLaMA 3.3 70B       |
            |      - Roadmap progress   |      |     - Heuristic audits    |
            +---------------------------+      +---------------------------+
```

---

## 📂 Repository Structure

```text
├── .github/                 # Automated CI workflows (verify.yml)
├── app/                     # Main Flask Application
│   ├── __init__.py          # App init, DB config, Auth setup, Error handlers
│   ├── models.py            # Relational database schemas (User, Resume, Roadmap, etc.)
│   ├── routes/              # Blueprints containing views and API controllers
│   │   ├── admin.py         # Admin Dashboard metrics & controls
│   │   ├── auth.py          # Secure student authentication logic
│   │   ├── dashboard.py     # Main student workspace
│   │   └── features.py      # Core AI engines (Roadmaps, Resumes, Interviews)
│   ├── static/              # CSS, JS, and Images
│   └── templates/           # Jinja2 HTML layout templates
├── scratch/                 # Local test scripts & endpoints testing
├── Dockerfile               # Production container build recipe (Gunicorn)
├── railway.json             # Railway app configurations and bindings
├── main.py                  # App entrypoint execution script
├── requirements.txt         # Locked project packages dependencies list
└── .env.example             # Template for secure environment variables
```

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

4. **Environment Variables:**
   Copy `.env.example` to `.env` and add your API keys. You can use Groq (Free) or Gemini (Free).
   ```bash
   cp .env.example .env
   ```

5. **Run the server:**
   ```bash
   python main.py
   ```
   Open **`http://127.0.0.1:8000`** in your browser.

---

## 🚀 Production Deployment

### Live Deployment via Railway
1. Click the **Deploy on Railway** button at the top of the README.
2. Grant Railway permissions to build from this fork.
3. Inject the environment variables (`GEMINI_API_KEY`, `SECRET_KEY`).
4. Railway will automatically build the container via the `Dockerfile` and publish an HTTPS endpoint using `gunicorn`.

---

<div align="center">
  <i>Built with ❤️ for the Microsoft Agents League.</i>
</div>
