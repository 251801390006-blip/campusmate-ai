<div align="center">
  <img src="https://img.shields.io/badge/CampusMate-AI-6366f1?style=for-the-badge&logo=openai&logoColor=white" alt="CampusMate AI Logo" />
  <h1>🎓 CampusMate AI</h1>
  <p><strong>The Premium, AI-Powered Student Career Operating System.</strong></p>

  [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new?template=https://github.com/251801390006-blip/campusmate-ai)
  [![Python Version](https://img.shields.io/badge/python-3.12-blue?style=flat-square&logo=python)](https://www.python.org/)
  [![Flask Version](https://img.shields.io/badge/Flask-3.0.3-009688?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
  [![Security Status](https://img.shields.io/badge/Security-100%25_Passed-brightgreen?style=flat-square&logo=shield)](https://github.com/251801390006-blip/campusmate-ai)
  [![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
</div>

---

## 🏆 Microsoft Agents League 2026 Submission

**Track:** Reasoning Agents  
**Status:** Submission Ready  
**Repository Visibility:** Public  
**Security Audit:** Passed  

### Why CampusMate AI Qualifies for the Reasoning Agents Track
CampusMate AI uses sophisticated AI-driven reasoning to analyze a student's long-term career goals. Instead of static content, it autonomously evaluates live resumes, identifies precise skill gaps, recommends personalized step-by-step learning roadmaps, and provides dynamic interview preparation guidance. The platform effectively acts as an autonomous career mentor reasoning through a student's educational lifecycle.

---

## 🎯 Problem Statement
Students constantly struggle with fragmented, disconnected tools for their professional development:
* Resume Building
* ATS Optimization
* Career Roadmapping
* Interview Preparation
* Internship Discovery

This causes disjointed career growth, wasted time across isolated platforms, and ultimately poor placement readiness.

---

## 💡 Solution
CampusMate AI unifies the entire student career journey inside a single, highly polished platform featuring:
* **ATS Resume Builder:** Production-ready one-page exports.
* **AI Resume Analyzer:** Live heuristic and AI-powered scoring.
* **Learning Roadmap Engine:** 200-node dynamic progression systems.
* **AI Interview Simulator:** Technical and HR practice.
* **Internship Command Center:** Skill-based opportunity matching.
* **Student Profile System:** Centralized achievement tracking.
* **Analytics Dashboard:** Administrative oversight.

---

## 🚀 Impact
CampusMate AI helps students:
* **Build ATS-friendly resumes** capable of passing automated HR filters.
* **Follow structured learning roadmaps** without getting lost in "tutorial hell."
* **Prepare for interviews** with realistic, simulated technical environments.
* **Discover internships** dynamically mapped to their current active skills.
* **Create professional portfolios** through a unified AI-powered career development platform.

---

## 📊 Platform Highlights
* **Multi-module career platform**
* **Responsive glassmorphic design**
* **Production Railway deployment**
* **Resume optimization system**
* **Interactive roadmap system**
* **Interview preparation tools**

---

## 📸 Screenshot Gallery & Features

### Platform Walkthrough
![Landing Page](./screenshots/01-landing-page.png)
*Glassmorphic Landing Page*

![Dashboard](./screenshots/04-dashboard.png)
*Centralized Student Dashboard*

### ATS Resume Builder & Analyzer
![Resume Builder Editor](./screenshots/05-resume-builder-editor.png)
*Live editing with professional ATS formats*

![ATS Analysis](./screenshots/07-ats-analysis.png)
*Resume scoring, keyword matching, and improvement suggestions*

### Roadmap Engine
![Roadmap Engine](./screenshots/09-roadmap-engine.png)
*Interactive 200-node progression system*

![Roadmap Resources](./screenshots/10-roadmap-resources.png)
*Step-by-step curated learning resources*

### AI Interview Simulator
![Interview Simulator](./screenshots/11-interview-simulator.png)
*Technical/HR interviews with voice-enabled practice*

### Internship Center
![Internship Center](./screenshots/12-internship-center.png)
*Opportunity matching and readiness scoring*

### Admin & Profile Management
![Profile Management](./screenshots/13-profile-management.png)
*Skill tracking and achievement management*

![Admin Dashboard](./screenshots/14-admin-dashboard.png)
*Platform analytics and security monitoring*

---

## 🏗️ System Architecture

![System Architecture](./screenshots/15-system-architecture.png)

The application flow leverages an efficient modular pipeline:

* **User Client:** Responsive frontend (HTML5/CSS3/Vanilla JS) initiating requests.
* **Frontend:** Glassmorphic UI layout with AJAX/Fetch API interceptors for smooth single-page UX.
* **Flask Backend:** Core Python WSGI server handling authentication, routing, and database sessions.
* **Career Modules:** Dedicated business logic components (Resume Engine, ATS Engine, Roadmap Engine, Analytics).
* **Database:** SQLite/PostgreSQL handling relational data models using SQLAlchemy ORM.
* **Analytics:** Aggregating student insights, engagement metrics, and system security health logs.

---

## ⚙️ Microsoft Technology Usage

* **Agent-Based Workflows:** Implementation of autonomous evaluation agents for resume parsing and interview simulation.
* **GitHub Copilot:** Extensively utilized during the development process to accelerate boilerplates, debug WSGI routes, and style frontend layouts.
* **AI-Assisted Development:** Employed generative models to refactor architecture and optimize database queries.
* **Reasoning-Driven Recommendations:** Uses intelligent prompt chains to analyze student inputs and synthesize structured JSON roadmaps.
* **Alignment with Microsoft Agents League:** Showcases the profound capability of AI agents applied directly to the education and career productivity sectors.

---

## 🌐 Deployment & Demo

* **Live Application URL:** [https://campusmate-ai-production.up.railway.app](https://campusmate-ai-production.up.railway.app)
* **GitHub Repository URL:** [https://github.com/251801390006-blip/campusmate-ai](https://github.com/251801390006-blip/campusmate-ai)
* **Deployment Platform:** Railway (Automated Containerized Builds)

### 🎥 Demo Video
> **[Watch the Full Platform Demo Here](#)**
*(Click to view the complete walkthrough demonstrating the Resume Builder, Roadmap Engine, and AI Interview features.)*

---

## 🛡️ Security

**Security Review: PASS**

Implemented:
* Environment Variable Protection
* Secret Key Hardening
* Upload Size Limits
* Session Protection
* Password Hashing
* Production Deployment Configuration

---

## 💻 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/251801390006-blip/campusmate-ai.git
   cd campusmate-ai
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS / Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Reference `.env.example` to set up your API keys. No secrets are exposed inside the repository.

5. **Run the server:**
   ```bash
   python main.py
   ```
   Open **`http://127.0.0.1:8000`** in your browser.

---

## 🔮 Future Scope
* **AI Voice Interview Agent:** Real-time conversational AI screening rounds.
* **Advanced Career Analytics:** Deep predictive insights on hiring trends.
* **Mentor Matching:** Connecting students with industry veterans.
* **Multi-language Support:** Accessible career tools for international students.
* **Enterprise University Integration:** Bulk deployment for college career centers.
* **Microsoft Foundry Integration:** Seamless enterprise AI scalability.

---

## 📜 License
MIT License
