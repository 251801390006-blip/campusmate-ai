# CampusMate AI
AI-Powered Student Career Operating System
Microsoft Agents League 2026 Submission

---

## Problem Statement
Students use disconnected tools for:
* Resume Building
* ATS Optimization
* Career Roadmapping
* Interview Preparation
* Internship Discovery

This causes fragmented career growth and poor placement readiness.

---

## Solution
CampusMate AI unifies:
* ATS Resume Builder
* AI Resume Analyzer
* Learning Roadmap Engine
* AI Interview Simulator
* Internship Command Center
* Student Profile System
* Analytics Dashboard

inside a single platform.

---

## Key Features

### ATS Resume Builder
Live editing
Professional templates
One-page ATS format
PDF export

![Resume Builder Editor](./screenshots/05-resume-builder-editor.png)

---

### Resume Live Preview
Real-time rendering
ATS-friendly formatting
Responsive preview

![Resume Builder Preview](./screenshots/06-resume-builder-preview.png)

---

### ATS Analyzer
Resume scoring
Keyword matching
Improvement suggestions

![ATS Analysis](./screenshots/07-ats-analysis.png)

---

### Professional PDF Export
Single-page ATS format
Production-ready layout
Consistent rendering

![Resume PDF Export](./screenshots/08-resume-pdf-export.png)

---

### Learning Roadmap Engine
200-node progression system
Career pathways
Milestone tracking

![Roadmap Engine](./screenshots/09-roadmap-engine.png)

---

### Roadmap Resource Explorer
Step-by-step learning resources
Curated references
Checkpoint guidance

![Roadmap Resources](./screenshots/10-roadmap-resources.png)

---

### AI Interview Simulator
Technical interviews
HR interviews
Voice-enabled practice

![Interview Simulator](./screenshots/11-interview-simulator.png)

---

### Internship Command Center
Opportunity matching
Readiness scoring
Skill-gap analysis

![Internship Center](./screenshots/12-internship-center.png)

---

### Student Profile System
Skill tracking
Achievement management
Career preferences

![Profile Management](./screenshots/13-profile-management.png)

---

### Admin Analytics Dashboard
Platform analytics
Security monitoring
Student insights

![Admin Dashboard](./screenshots/14-admin-dashboard.png)

---

## Platform Walkthrough

![Landing Page](./screenshots/01-landing-page.png)
![Dashboard](./screenshots/04-dashboard.png)

---

## Authentication System

![Login Page](./screenshots/02-login-page.png)
![Register Page](./screenshots/03-register-page.png)

---

## System Architecture

![System Architecture](./screenshots/15-system-architecture.png)

Cloudflare securely proxies traffic to our Railway instance where the Flask Backend orchestrates the Authentication Service and orchestrates the AI engines (Resume Engine, ATS Engine, Roadmap Engine, and Analytics Module). The system utilizes a dual-ready SQLite/PostgreSQL layer for rapid development and scalable production.

---

## Technology Stack

**Frontend**
* HTML5
* CSS3
* Bootstrap 5
* JavaScript

**Backend**
* Python
* Flask

**Database**
* SQLite
* PostgreSQL Ready

**AI Services**
* Gemini
* Microsoft Agent Ecosystem

**Deployment**
* Railway

---

## Security

**Implemented:**
* Environment Variable Protection
* Secret Key Hardening
* Upload Size Limits
* Session Protection
* Password Hashing
* Production Deployment Configuration

**Security Audit Status:**
`PASS`

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/251801390006-blip/campusmate-ai.git
   cd campusmate-ai
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # macOS / Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server:**
   ```bash
   python main.py
   ```
   Open `http://127.0.0.1:8000` in your browser.

---

## Environment Variables
Reference `.env.example`. No secrets inside repository.

---

## Demo
Live Application: https://campusmate-ai-production.up.railway.app

---

## License
MIT License

---

## Microsoft Agents League Submission
**Track:** AI Career Growth & Student Productivity
**Status:** Submission Ready
**Repository Visibility:** Public
**Security Audit:** Passed
**Documentation:** Complete
**Deployment:** Live
