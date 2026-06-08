# CampusMate AI 2.0
> The Premium AI Career & Learning Operating System for Students.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new?template=https://github.com/251801390006-blip/campusmate-ai)

CampusMate AI is a premium SaaS-style student growth engine. It is designed to act as an offline-first learning system and a connected AI career helper, supporting visual roadmaps, automated resume scoring, live mock interviews, and system design advice.

---

## 🌟 Key Features

*   **AI Mentor Coach 2.0**: Chat drawer featuring streaming typewriter text output, suggestions chips, conversation history persistence, and a brain memory context ribbon.
*   **Double-Mode ATS Resume Builder**: Create templates from scratch or drag-and-drop PDF/DOCX files. Simulates keyword auditing and grades readability.
*   **Expandable Roadmap Engine 2.0**: Supports 8 professional track paths (Cyber, AI, ML, Data Science, Cloud, DevOps, Full Stack, and Mobile Dev) with interactive checkpoints, tasks, and aligned certifications.
*   **Connected & Standalone Modes**: Runs 100% locally in Sandbox Mode (saving states in browser `localStorage`), or syncs with a FastAPI server using SQLite.

---

## 🚀 One-Click Deploy on Railway

1.  Click the **Deploy on Railway** button above.
2.  Log in with your GitHub account.
3.  Fill in the **`GEMINI_API_KEY`** environment variable (optional, for live AI responses).
4.  Railway will read the `Dockerfile`, install python dependencies, compile native modules, and serve the application live on a secure HTTPS URL.

---

## 💻 Local Setup & Development

### 1. Initialize Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Backend Server
```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```
Open **`http://127.0.0.1:8000`** in your web browser. If the backend is offline, you can double-click **`static/index.html`** to run in offline Sandbox mode!
