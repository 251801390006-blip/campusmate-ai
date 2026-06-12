import os
import io
import re
import json
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, abort, make_response
from flask_login import login_required, current_user
from app.models import db, User, ChatMessage, ResumeAnalysis, RoadmapProgress, UserResume, Internship, SavedItem
from pypdf import PdfReader
try:
    import weasyprint
except Exception:
    weasyprint = None
from io import BytesIO

features_bp = Blueprint('features', __name__)

# --- AI CLIENT WRAPPER (supports Groq + Gemini) ---
def call_gemini(system_prompt: str, user_prompt: str, user_key: str = None) -> str:
    """
    Multi-provider AI router.
    Priority: user_key → DB global key → env var GEMINI_API_KEY → env var GROQ_API_KEY
    - Groq key  (starts with gsk_) → Groq LLaMA 3.3-70B (free)
    - Gemini key (AIza...)          → Google Gemini 2.5 Flash
    - No key anywhere               → returns '' to trigger offline message
    """
    api_key = user_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY")
    # Last resort: read global key saved by admin in the database
    if not api_key:
        try:
            from app.models import SiteConfig
            api_key = SiteConfig.get('global_ai_key', '') or ''
        except Exception:
            pass
    if not api_key:
        return ""  # No key anywhere — trigger offline message

    # ── Groq (free, fast, any personal email) ──────────────────────────────
    if api_key.startswith("gsk_"):
        try:
            import urllib.request as urllib_req
            import json as json_lib
            payload = json_lib.dumps({
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 1024
            }).encode("utf-8")
            req = urllib_req.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib_req.urlopen(req, timeout=30) as resp:
                data = json_lib.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Groq API call failed: {e}")
            return ""

    # ── Google Gemini ───────────────────────────────────────────────────────
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2
            )
        )
        return response.text
    except Exception as e:
        print(f"Gemini API call failed: {e}")
        return ""


# --- PARSING HELPERS ---
def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return ""

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        docx_file = io.BytesIO(file_bytes)
        with zipfile.ZipFile(docx_file) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            texts = []
            for paragraph in root.findall('.//w:p', namespaces):
                p_text = ""
                for run in paragraph.findall('.//w:t', namespaces):
                    if run.text:
                        p_text += run.text
                if p_text:
                    texts.append(p_text)
            return "\n".join(texts).strip()
    except Exception as e:
        print(f"Error parsing DOCX: {e}")
        return ""

# --- ATS SCORING HEURISTIC ---
def heuristic_parse_resume(text: str) -> dict:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # Extract email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    email = email_match.group(0) if email_match else ""
    
    # Extract phone
    phone_match = re.search(r'\+?\d[\d\-\s\(\)]{7,}\d', text)
    phone = phone_match.group(0) if phone_match else ""
    
    # Extract links
    github_match = re.search(r'github\.com/[\w\.-]+', text, re.IGNORECASE)
    github = "https://" + github_match.group(0) if github_match else ""
    
    linkedin_match = re.search(r'linkedin\.com/in/[\w\.-]+', text, re.IGNORECASE)
    linkedin = "https://" + linkedin_match.group(0) if linkedin_match else ""
    
    # Name heuristic
    name = "Alex Smith"
    for line in lines[:5]:
        if '@' not in line and 'http' not in line and '|' not in line and len(line) < 50:
            name = line
            break
            
    # Segment sections
    sections = {
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [],
        "certifications": []
    }
    
    current_section = None
    for line in lines:
        line_lower = line.lower()
        if any(h in line_lower for h in ["education", "academic", "university", "college"]):
            current_section = "education"
        elif any(h in line_lower for h in ["experience", "employment", "work history", "career"]):
            current_section = "experience"
        elif any(h in line_lower for h in ["projects", "personal projects", "portfolio"]):
            current_section = "projects"
        elif any(h in line_lower for h in ["skills", "technical skills", "languages", "technologies"]):
            current_section = "skills"
        elif any(h in line_lower for h in ["certifications", "certs", "credentials"]):
            current_section = "certifications"
        elif current_section:
            sections[current_section].append(line)
            
    # Key word scanning
    all_skills_text = " ".join(sections["skills"]) if sections["skills"] else text
    
    prog_keywords = ["python", "javascript", "typescript", "java", "c++", "c#", "rust", "go", "ruby", "php"]
    cyber_keywords = ["wireshark", "nmap", "metasploit", "penetration testing", "cybersecurity", "firewall", "snort", "cryptography"]
    os_keywords = ["linux", "windows", "macos", "ubuntu", "debian", "redhat"]
    tools_keywords = ["git", "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "jenkins", "ansible"]
    web_keywords = ["react", "vue", "angular", "fastapi", "django", "flask", "node", "express", "html", "css"]
    
    found_prog = [k.capitalize() for k in prog_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    found_cyber = [k.capitalize() for k in cyber_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    found_os = [k.capitalize() for k in os_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    found_tools = [k.capitalize() for k in tools_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    found_web = [k.capitalize() for k in web_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    
    # Base calculation
    score = 45
    if email: score += 5
    if phone: score += 5
    if github or linkedin: score += 5
    if sections["education"]: score += 10
    if sections["experience"]: score += 15
    if sections["projects"]: score += 10
    if sections["skills"]: score += 10
    
    words_count = len(text.split())
    if words_count > 300: score += 15
    elif words_count > 150: score += 10
    elif words_count > 50: score += 5
        
    action_verbs = ["implemented", "developed", "designed", "architected", "optimized", "managed", "created", "built", "engineered", "collaborated"]
    found_verbs = [v for v in action_verbs if v in text.lower()]
    score += min(len(found_verbs) * 2, 10)
    score = min(score, 98)
    
    readability = min(65 + len(found_verbs) * 3 + (10 if len(lines) > 20 else 0), 96)
    industry_match = min(50 + len(found_prog + found_cyber + found_tools + found_web) * 3, 98)
    
    missing_keywords = []
    if not found_tools: missing_keywords.extend(["Docker", "Git"])
    if not found_web: missing_keywords.extend(["FastAPI", "React"])
    if not found_cyber: missing_keywords.extend(["Nmap", "Wireshark"])
    if len(missing_keywords) < 3:
        missing_keywords.extend(["CI/CD Pipelines", "SQLModel", "Cloud Deployment"])
    missing_keywords = list(set(missing_keywords))[:4]
    
    improvements = []
    weak_verbs = ["worked on", "helped", "responsible for", "assisted", "did"]
    for line in lines:
        for wv in weak_verbs:
            if wv in line.lower() and len(improvements) < 2:
                improvements.append({
                    "originalText": line,
                    "suggestedText": "Engineered automated workflows and collaborated on full systems delivery.",
                    "reason": "Replaced weak passive verbs with strong action verbs."
                })
                
    if not improvements:
        improvements.append({
            "originalText": "Responsible for coding the backend of the student project application.",
            "suggestedText": "Architected performant relational database schemas and API routing structures in Flask, reducing API controller latency by 20%.",
            "reason": "Uses passive phrasing. Suggested action verbs and concrete achievement metrics."
        })
        
    mistakes = []
    if not email: mistakes.append("Contact email address is missing.")
    if not phone: mistakes.append("Phone contact number is missing.")
    if not github: mistakes.append("Missing link to GitHub portfolio.")
    if len(found_verbs) < 3: mistakes.append("Too few strong action verbs used in descriptions.")
    if words_count < 100: mistakes.append("Resume contains very low detail. Expand on achievements.")
    if not mistakes:
        mistakes.append("Vague/passive verb constructs used in experience description (e.g., 'Responsible for', 'Helped').")
        mistakes.append("Lack of quantitative outcomes/metrics to prove efficiency gains.")
        
    suggestions = [
        "Replace passive phrases with strong engineering action verbs like 'Engineered', 'Optimized', or 'Automated'.",
        "Apply the Google XYZ formula to quantify your achievements (e.g., 'increased throughput by X%').",
        "Format technical skills into distinct, scan-friendly categories."
    ]
    
    formatting_score = min(100, 70 + (5 if email else 0) + (5 if phone else 0) + (10 if github or linkedin else 0) + (10 if words_count > 150 else 0))
    skills_score = min(100, max(30, 50 + len(found_prog + found_cyber + found_tools + found_web) * 4))
    keyword_score = industry_match
    project_quality_score = min(100, max(40, 60 + len(found_verbs) * 4))

    return {
        "atsScore": score,
        "formattingScore": formatting_score,
        "skillsScore": skills_score,
        "keywordScore": keyword_score,
        "readabilityScore": readability,
        "projectQualityScore": project_quality_score,
        "industryMatchScore": industry_match,
        "name": name,
        "email": email or "student@university.edu.in",
        "phone": phone or "+91 98765 43210",
        "github": github or "https://github.com/student",
        "linkedin": linkedin or "https://linkedin.com/in/student",
        "skillsProg": ", ".join(found_prog) or "Python, C++",
        "skillsCyber": ", ".join(found_cyber) or "Firewall Configuration",
        "skillsOs": ", ".join(found_os) or "Linux",
        "skillsTools": ", ".join(found_tools) or "Git, Docker",
        "skillsWeb": ", ".join(found_web) or "Flask, React",
        "missingKeywords": missing_keywords,
        "improvements": improvements,
        "mistakes": mistakes,
        "suggestions": suggestions
    }

def parse_text_to_resume_fields(text: str) -> dict:
    parsed = heuristic_parse_resume(text)
    
    # Base defaults
    fields = {
        "name": parsed.get("name", "Alex Smith"),
        "address": "San Francisco, California, USA",
        "email": parsed.get("email", ""),
        "phone": parsed.get("phone", ""),
        "linkedin": parsed.get("linkedin", ""),
        "github": parsed.get("github", ""),
        
        "edu1Inst": "State Tech University",
        "edu1Degree": "B.S. in Computer Science",
        "edu1Dates": "2024 – 2028",
        "edu1Gpa": "3.8/4.0",
        "edu1Coursework": "Data Structures, Cryptography, Database Systems, Computer Networks",
        
        "edu2Inst": "",
        "edu2Degree": "",
        "edu2Dates": "",
        "edu2Gpa": "",
        
        "skillsProg": parsed.get("skillsProg", ""),
        "skillsCyber": parsed.get("skillsCyber", ""),
        "skillsOs": parsed.get("skillsOs", ""),
        "skillsTools": parsed.get("skillsTools", ""),
        "skillsWeb": parsed.get("skillsWeb", ""),
        
        "experienceRole": "Software Engineering Intern",
        "experienceComp": "Global Tech Solutions",
        "experienceDates": "June 2025 – August 2025",
        "experienceB1": "",
        "experienceB2": "",
        "experienceB3": "",
        "experienceB4": "",
        
        "projectTitle": "CampusMate AI – Student Learning Workspace",
        "projectLink": "github.com/alexsmith/campusmate-ai",
        "projectB1": "",
        "projectB2": "",
        "projectB3": "",
        
        "certC1": "",
        "certC2": "",
        "certC3": "",
        "certC4": "",
        
        # New details sections default initializations
        "profilePic": "",
        "portfolio": "",
        "achievements": "Dean's List 2025, First Place CodeQuest Hackathon",
        "researchPapers": "Decentralized Threat Log Mapping (IEEE 2026)",
        "hackathons": "Participated in DevFest 24, Smart India Hackathon 25",
        "workshops": "Attended AWS Cloud Practitioner Immersion Day",
        "volunteering": "Tech mentor at local high school coding club",
        "languages": "English (Fluent), Spanish (Conversational)",
        "interests": "Cryptography, Robotics, Open Source Contributing",
        "references": "Available upon request",
        "custom": ""
    }
    
    # Try to extract sections dynamically from text
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    # Split text by sections
    section_map = {}
    current_sec = None
    for l in lines:
        l_lower = l.lower()
        if any(x in l_lower for x in ["education", "academic", "university", "college"]):
            current_sec = "edu"
        elif any(x in l_lower for x in ["experience", "employment", "work", "career"]):
            current_sec = "exp"
        elif any(x in l_lower for x in ["projects", "personal projects", "portfolio"]):
            current_sec = "proj"
        elif any(x in l_lower for x in ["skills", "technical skills", "languages", "technologies"]):
            current_sec = "skills"
        elif any(x in l_lower for x in ["certifications", "certs", "credentials", "achievements"]):
            current_sec = "cert"
        elif current_sec:
            section_map.setdefault(current_sec, []).append(l)
            
    # Assign education
    edu_lines = section_map.get("edu", [])
    if edu_lines:
        fields["edu1Inst"] = edu_lines[0]
        if len(edu_lines) > 1:
            fields["edu1Degree"] = edu_lines[1]
        if len(edu_lines) > 2:
            fields["edu1Dates"] = edu_lines[2]
            
    # Assign experience
    exp_lines = section_map.get("exp", [])
    if exp_lines:
        fields["experienceRole"] = exp_lines[0]
        if len(exp_lines) > 1 and not exp_lines[1].startswith(("-", "*", "•")):
            fields["experienceComp"] = exp_lines[1]
        bullets = [l for l in exp_lines[1:] if l.startswith(("-", "*", "•")) or len(l) > 30]
        if len(bullets) > 0: fields["experienceB1"] = bullets[0].lstrip("-*• ")
        if len(bullets) > 1: fields["experienceB2"] = bullets[1].lstrip("-*• ")
        if len(bullets) > 2: fields["experienceB3"] = bullets[2].lstrip("-*• ")
        if len(bullets) > 3: fields["experienceB4"] = bullets[3].lstrip("-*• ")
        
    # Assign projects
    proj_lines = section_map.get("proj", [])
    if proj_lines:
        fields["projectTitle"] = proj_lines[0]
        bullets = [l for l in proj_lines[1:] if l.startswith(("-", "*", "•")) or len(l) > 30]
        if len(bullets) > 0: fields["projectB1"] = bullets[0].lstrip("-*• ")
        if len(bullets) > 1: fields["projectB2"] = bullets[1].lstrip("-*• ")
        if len(bullets) > 2: fields["projectB3"] = bullets[2].lstrip("-*• ")
        
    # Assign certifications
    cert_lines = section_map.get("cert", [])
    if cert_lines:
        if len(cert_lines) > 0: fields["certC1"] = cert_lines[0]
        if len(cert_lines) > 1: fields["certC2"] = cert_lines[1]
        if len(cert_lines) > 2: fields["certC3"] = cert_lines[2]
        if len(cert_lines) > 3: fields["certC4"] = cert_lines[3]
        
    return fields

# --- ROADMAP DETAIL CONTEXTS ---
def get_predefined_roadmap(role: str) -> list:
    role_lower = role.lower()
    
    # 1. Cyber Security
    if "cyber" in role_lower or "security" in role_lower:
        milestones = [
            ("Networking & OSI Model Essentials", "Master TCP/IP, subnets, DNS, and OSI layer fundamentals."),
            ("IP Subnetting & Packet Routing", "Learn how routers direct packets across subnets and local area networks."),
            ("Common Protocols & Audits", "Examine and audit DNS, HTTP, SSH, FTP, and DHCP protocols."),
            ("Command Line & Bash Scripting", "Master Linux file navigation, permissions, and automation scripts."),
            ("Windows Security & PowerShell", "Learn Windows active directory administration and powershell commands."),
            ("Intro to Cryptography & Keys", "Differentiate symmetric vs asymmetric encryption and key exchange."),
            ("Hashing & Integrity Verification", "Use SHA, MD5, and digital signatures to audit document integrity."),
            ("Reconnaissance & Nmap Scanning", "Scan open ports, discover OS versions, and catalog target assets."),
            ("Packet Sniffing with Wireshark", "Capture and analyze network frames to trace protocol payloads."),
            ("Firewall ACLs & Segmentation", "Configure network security groups and block unauthorized port access."),
            ("SSH Hardening & Security Audits", "Audit SSH configuration, disable root login, and enforce key auth."),
            ("Identity Access Management (IAM)", "Configure multi-factor auth, role bindings, and credential policies."),
            ("OWASP Top 10 Security Risks", "Understand SQL injection, XSS, and broken access controls."),
            ("SQL Injection & Defensive Coding", "Exploit SQL weaknesses and implement parameterized query overrides."),
            ("Metasploit Framework Exploitation", "Configure exploit modules, payloads, and establish shell listeners."),
            ("Wireless WPA2/WPA3 Security", "Learn security handshakes, packet capture, and deauth attacks."),
            ("IDS/IPS Snort Rules Configuration", "Create snort signatures to flag and block network attack profiles."),
            ("SIEM Log Auditing with Splunk", "Index server logs and create alerts for suspicious login behaviors."),
            ("Threat Hunting & Log Correlation", "Correlate syslog and auth logs to map persistent attack paths."),
            ("Malware Analysis: Static Review", "Analyze PE headers, string hashes, and import tables of binaries."),
            ("Malware Analysis: Dynamic Scans", "Run binaries in a secure sandbox and monitor registry changes."),
            ("Cloud Shared Responsibility Models", "Audit AWS and Azure security frameworks and identity bindings."),
            ("Cloud Gateways & WAF Security", "Deploy web application firewalls and lock down virtual networks."),
            ("Penetration Testing Scope & Ethics", "Learn scopes of work, reporting standards, and legal compliance."),
            ("Purple Teaming & Incident Response", "Collaborate on attack/defense simulations and incident reporting."),
            ("Capstone: Cyber Defense Project", "Perform a comprehensive security audit of a staging website infrastructure.")
        ]
        provider = "CompTIA / EC-Council"
        cert = "CompTIA Security+"
    # 2. AI Engineering
    elif "ai engineering" in role_lower or "ai engineer" in role_lower:
        milestones = [
            ("Python Programming & Tool Setup", "Install dependencies, write syntax commands, and configure VS Code."),
            ("Control Flow & Logic in Python", "Write conditionals, loops, and conditional flow logic statements."),
            ("Functions & Modular File Structures", "Create modular python functions, scripts, and exception boundaries."),
            ("OOP Principles & Custom Classes", "Use classes, inheritance, and object abstractions in Python."),
            ("File Parsing: JSON, CSV, & Files", "Read local log files and clean structured telemetry inputs."),
            ("NumPy Vectorized Array Workflows", "Create matrices, compute dot products, and optimize loops."),
            ("Pandas DataFrames & Aggregations", "Load tabular data, group stats, and index complex datasets."),
            ("Data Visualization with Seaborn", "Plot correlation heatmaps, line charts, and bar diagrams."),
            ("Linear Algebra for Model Weights", "Compute matrix determinants, eigenvalues, and dot multiplications."),
            ("Gradient Descent Optimizations", "Learn loss functions, derivatives, and learning rates."),
            ("Probability Foundations for Models", "Calculate Bayes theorem probabilities and normal distributions."),
            ("Supervised Learning Regression Models", "Train linear regression models using Scikit-Learn."),
            ("Decision Trees & Ensemble Forests", "Train classifier models and verify split indices."),
            ("Support Vector Classification", "Configure hyperplanes and kernel transformations."),
            ("Unsupervised Clustering Algorithms", "Group data rows using K-Means and DBSCAN algorithms."),
            ("Dimensionality Reduction with PCA", "Condense feature columns while preserving data variance."),
            ("ROC, AUC & F1-Score Evaluations", "Construct confusion matrices and optimize threshold curves."),
            ("Introduction to PyTorch Tensors", "Setup tensor structures, auto-differentiation, and backpropagation."),
            ("Convolutional Image Neural Networks", "Construct CNN layers for computer vision digit classifications."),
            ("RNNs & LSTMs for Time-Series", "Train sequential networks to predict stock trends or logs."),
            ("NLP Tokenization & Embeddings", "Convert text inputs to vector tokens and bag-of-words."),
            ("Transformer Encoder-Decoder Layers", "Learn self-attention mechanisms and query-key-value vectors."),
            ("Prompt Engineering & System Prompts", "Create system instructions for LLM completions."),
            ("RAG Pipelines & Vector Databases", "Retrieve local PDF text chunks and search ChromaDB vectors."),
            ("Exposing Models via FastAPI Docker", "Wrap model inference scripts inside FastAPI and run via Docker."),
            ("Capstone: Interactive RAG Assistant", "Deploy a functional question-answering assistant over custom files.")
        ]
        provider = "Microsoft / Google"
        cert = "Azure AI Engineer Associate"
    # 3. Machine Learning
    elif "machine" in role_lower or "ml" in role_lower:
        milestones = [
            ("Python Setup & Jupyter Notebooks", "Configure environments, install pip packages, and write cells."),
            ("Variables, Lists & Loops in Python", "Work with python sequences, slicing, and dictionaries."),
            ("Functions, Errors & Imports", "Define custom methods, raise exceptions, and load modules."),
            ("NumPy Arrays & Linear Algebra", "Execute matrix arithmetic, reshape tensors, and select slices."),
            ("Pandas Data Analytics Essentials", "Filter rows, map column values, and handle NaN placeholders."),
            ("Data Visualization & Distributions", "Construct histograms, scatter plots, and box plots."),
            ("Linear & Polynomial Regressions", "Perform curve fitting and compute mean squared error metrics."),
            ("Logistic Regression & Binary Targets", "Train sigmoid models to classify user churn anomalies."),
            ("Decision Trees & Hyperparameters", "Prune tree nodes, configure min_samples, and plot rules."),
            ("Random Forests & Bagging Methods", "Combine tree predictors and inspect feature importances."),
            ("Support Vector Machines & Kernels", "Configure radial basis functions and margin soft parameters."),
            ("K-Means Clustering & Elbow Curves", "Segment user segments and compute inertia scores."),
            ("Principal Component Analysis (PCA)", "Reduce dimensions and analyze explained variance ratios."),
            ("Overfitting & Cross-Validation", "Run K-Fold validations and diagnose train/test curves."),
            ("Stochastic Gradient Descent (SGD)", "Optimize loss parameters using mini-batches."),
            ("PyTorch Neural Networks Basics", "Define linear layers, activation functions, and optimizer hooks."),
            ("Training Custom CNN Model Layers", "Build convolution and pooling loops for image inputs."),
            ("LSTMs & Text Generation loops", "Setup sequence-to-sequence neural architectures."),
            ("Feature Engineering & Scaling", "Apply StandardScalers, one-hot encoders, and log fixes."),
            ("Model Serialization & Joblib", "Export weights files and write fast loading hooks."),
            ("FastAPI Inference Controllers", "Deploy a backend route that loads model weights and classifies."),
            ("Dockerizing ML Service Environs", "Build clean container layers containing model assets."),
            ("Deploying ML models to Cloud VM", "Run inference containers on cloud servers behind proxy gates."),
            ("Monitoring Model Drift telemetry", "Setup dashboard tracking for live prediction confidence graphs."),
            ("Advanced Hyperparameter Search", "Run Optuna, grid searches, and optimize batch size metrics."),
            ("Capstone: Production ML Deploy", "Deploy an end-to-end model pipeline that continuously predicts churn.")
        ]
        provider = "Google Cloud / AWS"
        cert = "GCP Professional Machine Learning Engineer"
    # 4. Data Science
    elif "data science" in role_lower or "data scientist" in role_lower:
        milestones = [
            ("Python & Jupyter Basics", "Configure notebooks, install pandas/matplotlib, and write scripts."),
            ("Pandas: Loading & Selecting Data", "Read CSV/JSON files, inspect head, and select columns."),
            ("Pandas: Data Cleaning Strategies", "Drop duplicate rows, fill missing cells, and change types."),
            ("Exploratory Data Analysis (EDA)", "Create correlation heatmaps and identify data anomalies."),
            ("Matplotlib & Seaborn Custom Plots", "Customize chart colors, labels, axes, and legends."),
            ("SQL: Querying Databases for Analysis", "Write SELECT statements, filter conditions, and limits."),
            ("SQL: Joins, Groups & Aggregations", "Combine tables using INNER/LEFT JOIN and count metrics."),
            ("Descriptive Statistics Foundations", "Calculate mean, median, mode, variance, and standard deviation."),
            ("Probability Distributions & Z-Scores", "Analyze normal distributions, outliers, and normalize scales."),
            ("Hypothesis Testing & T-Tests", "Set null hypotheses, calculate p-values, and check significance."),
            ("A/B Testing Experiments Design", "Determine sample sizes, control groups, and verify conversions."),
            ("Linear Regression & Correlation", "Assess Pearson correlation and fit regression lines."),
            ("Logistic Regression Classifications", "Predict binary classifications and plot confusion matrices."),
            ("Decision Trees for Analytics", "Create rule trees and print feature importance lists."),
            ("Time Series Analysis & Forecasting", "Decompose trends, seasonal cycles, and run ARIMA models."),
            ("Text Mining & Basic NLP Analysis", "Clean text strings, remove stopwords, and build wordclouds."),
            ("Dimensionality Reduction & Clustering", "Run PCA and group customer behavior using K-Means."),
            ("Feature Selection Techniques", "Filter features using ANOVA, chi-square, and mutual info."),
            ("Data Pipelines: ETL Essentials", "Extract raw files, transform schema mappings, and save to SQL."),
            ("Intro to Big Data & Spark DataFrames", "Run distributed queries on large datasets using PySpark."),
            ("BI Tools: Building Dashboard Mockups", "Design visual tracking widgets for business managers."),
            ("Deploying Analytical Reports as APIs", "Expose key stats, summaries, and predictions via FastAPI."),
            ("Dockerizing ETL Script Containers", "Containerize data import scripts to run on daily schedules."),
            ("Cloud Data Warehouse Foundations", "Learn query configurations for AWS Redshift or Google BigQuery."),
            ("Capstone: Interactive Data Dashboard", "Deliver a comprehensive project featuring clean ETL and plots."),
            ("Capstone Project Presentation", "Present a clean analytical model summarizing insights of a 10M row logs database.")
        ]
        provider = "Microsoft / Databricks"
        cert = "Microsoft Certified: Power BI Data Analyst Associate"
    # 5. Cloud Computing
    elif "cloud" in role_lower:
        milestones = [
            ("Cloud Computing Fundamentals", "Learn IaaS, PaaS, SaaS, and public vs private structures."),
            ("Virtual Machines & OS Provisioning", "Spin up VMs, configure SSH access, and update repositories."),
            ("Virtual Networking & Subnetting", "Deploy virtual networks, design subnets, and configure routes."),
            ("Firewalls & Network Access Control", "Configure ingress/egress rules and block open SSH ports.")
        ]
        provider = "Amazon Web Services"
        cert = "AWS Certified Solutions Architect"
    else:
        milestones = [
            ("Web Architecture & HTTP Protocols", "Learn how web requests travel over TCP and DNS infrastructure."),
            ("HTML5 & CSS Grid Layouts", "Build responsive layouts using semantic grids and CSS variables."),
            ("JavaScript Core & DOM Operations", "Write asynchronous promises and event handlers."),
            ("REST APIs with Flask or Express", "Configure HTTP routing, controllers, and JSON responses.")
        ]
        provider = "Meta"
        cert = "Meta Front-End Developer Certificate"

    # Map tracks to distinct stages
    if "cyber" in role_lower or "security" in role_lower or "hacking" in role_lower or "soc" in role_lower or "forensics" in role_lower or "network" in role_lower or "linux" in role_lower:
        track_type = "security"
    elif "ai" in role_lower or "intelligence" in role_lower or "machine" in role_lower or "deep" in role_lower or "learning" in role_lower or "prompt" in role_lower or "agentic" in role_lower or "analytics" in role_lower or "data" in role_lower:
        track_type = "data_ai"
    elif "cloud" in role_lower or "aws" in role_lower or "azure" in role_lower or "google" in role_lower or "devops" in role_lower or "kubernetes" in role_lower or "docker" in role_lower or "reliability" in role_lower:
        track_type = "cloud_ops"
    elif "blockchain" in role_lower or "web3" in role_lower:
        track_type = "web3"
    elif "design" in role_lower or "product" in role_lower or "testing" in role_lower or "qa" in role_lower or "business" in role_lower or "sap" in role_lower or "salesforce" in role_lower:
        track_type = "product_qa"
    elif "vlsi" in role_lower or "ece" in role_lower or "electrical" in role_lower or "electronics" in role_lower or "power systems" in role_lower or "circuits" in role_lower or "robotics" in role_lower or "iot" in role_lower or "embedded" in role_lower:
        track_type = "hardware_ece"
    elif "csbs" in role_lower or "bio science" in role_lower or "biotech" in role_lower or "biological" in role_lower or "bioinformatics" in role_lower or "medical" in role_lower or "biomedical" in role_lower:
        track_type = "csbs"
    elif "mechanical" in role_lower or "civil" in role_lower or "chemical" in role_lower or "systems engineering" in role_lower or "aerospace" in role_lower or "automotive" in role_lower or "renewable" in role_lower or "nuclear" in role_lower or "marine" in role_lower or "environmental" in role_lower or "materials" in role_lower:
        track_type = "traditional_eng"
    elif "quantum" in role_lower:
        track_type = "quantum"
    else:
        track_type = "dev" # standard programming and full-stack development

    # Stage themes
    if track_type == "security":
        beginner_themes = [
            "Networking Foundations & OSI Model", "IP Routing & Local Subnets",
            "Command Line Interfaces & Linux Bash", "Basic Cryptography & Hashing Keys",
            "Port Scanning & Reconnaissance Tools", "Wireshark Packet Analysis Techniques"
        ]
        inter_themes = [
            "Firewall Policy Controls & VPNs", "OWASP Top 10 Web Vulnerabilities",
            "Access Control Lists & IAM Policies", "Intrusion Detection Systems (IDS/IPS)",
            "System Log Auditing & Splunk Basics", "Cloud Security Configuration Hardening"
        ]
        adv_themes = [
            "Active Directory Intrusion Testing", "Reverse Engineering & Assembly Basics",
            "Malware Signature Recognition", "Buffer Overflow Vulnerability Exploitations",
            "Advanced Penetration Testing Frameworks"
        ]
        prof_themes = [
            "Threat Hunting & Incident Response", "SaaS DevSecOps Compliance Rules",
            "Zero-Downtime Incident Failovers", "OSCP Capstone Laboratory Preparation"
        ]
        cert_name = "CompTIA Security+"
        cert_provider = "CompTIA"
    elif track_type == "data_ai":
        beginner_themes = [
            "Linear Algebra & Statistical Basics", "Python Foundations & Numpy Arrays",
            "Pandas Data Wrangling & Cleaning", "SQL Queries & Databases Operations",
            "Scikit-Learn Machine Learning Models", "Regression & Classification Metrics"
        ]
        inter_themes = [
            "Neural Network Architecture Basics", "PyTorch Framework & Deep Learning",
            "Computer Vision & Convolutional Nets", "Recurrent Neural Networks & NLP",
            "Model Fine-Tuning Hyperparameters", "Vector Databases & Semantic Embeddings"
        ]
        adv_themes = [
            "Transformer Models & Attention Layers", "Generative AI & LLMs Architecture",
            "Retrieval Augmented Generation (RAG)", "Agentic AI Autopilot Multi-Agent Frameworks",
            "Model Optimizations & Quantization"
        ]
        prof_themes = [
            "AI Deployment Pipelines & Kubernetes", "Model Monitoring & Drift Detection",
            "Bias Mitigation & AI Ethics Guidelines", "Production Capstone LLM Deployment"
        ]
        cert_name = "Microsoft Certified: Azure AI Engineer"
        cert_provider = "Microsoft"
    elif track_type == "cloud_ops":
        beginner_themes = [
            "Networking Essentials & IP Subnets", "Virtual Machines & Hypervisors",
            "Linux Commands & File Hardening", "Cloud Storage Buckets & Permissions",
            "Docker Containers Foundations", "Git Version Control Operations"
        ]
        inter_themes = [
            "YAML Manifests & Shell Scripting", "Infrastructure as Code (IaC) Basics",
            "Terraform Deployments & States", "Ansible Configuration Playbooks",
            "Continuous Integration (CI) Actions", "Kubernetes Pods & Services"
        ]
        adv_themes = [
            "Kubernetes ConfigMaps & Secret Variables", "Ingress Controllers & Domain Routing",
            "SRE SLOs/SLIs System Health Metrics", "Prometheus & Grafana Dashboards",
            "Jenkins Deployment Pipeline Scripts"
        ]
        prof_themes = [
            "GitOps ArgoCD Automatic Sync", "Vulnerability Scanning inside Pipelines",
            "Multi-Region Cloud Deployments", "DevOps Production Pipeline Capstone"
        ]
        cert_name = "AWS Certified Solutions Architect"
        cert_provider = "Amazon Web Services"
    elif track_type == "web3":
        beginner_themes = [
            "Cryptography & Hash Functions", "Decentralized Ledger Architecture",
            "Bitcoin Protocol & Transactions", "Ethereum Virtual Machine Foundations",
            "Solidity Language Syntax Variables", "Smart Contracts Basic Topics"
        ]
        inter_themes = [
            "Web3.js & Ethers.js Interfaces", "MetaMask Wallet API Binding",
            "ERC-20 & ERC-721 Token Standard", "IPFS Decentralized File Hosting",
            "Truffle & Hardhat Local Dev Test", "Smart Contract Security Vulnerabilities"
        ]
        adv_themes = [
            "Defi Pools & Automated Market Makers", "Decentralized Autonomous Organizations (DAOs)",
            "Layer-2 Rollups & Scaling Pipelines", "Smart Contract Gas Fee Optimizations",
            "Oracles & ChainLink API Integration"
        ]
        prof_themes = [
            "Smart Contract Security Audits", "ZK-Rollups & Zero-Knowledge Proofs",
            "Web3 DApp Complete Deployment", "Web3 Capstone Production Auditor"
        ]
        cert_name = "Certified Blockchain Developer"
        cert_provider = "Blockchain Council"
    elif track_type == "product_qa":
        beginner_themes = [
            "Product Lifecycle & Agile Scrum", "User Research & Persona Mappings",
            "Figma Wireframes & Page Layouts", "Software Quality Assurance Basics",
            "Manual Test Cases & Bug Trackers", "Database Indexing & Queries"
        ]
        inter_themes = [
            "QA Automation Selenium Scripts", "Playwright Visual Test Suites",
            "SaaS Product Metrics & LTV/CAC", "Business Process Mapping (BPMN)",
            "SAP Module Layouts & ERP Basics", "Salesforce Apex Scripting Triggers"
        ]
        adv_themes = [
            "Load Testing & JMeter Performance", "API Mocking & Postman Automation",
            "Product Roadmap Backlog Pruning", "ERP Database Integration Pipelines",
            "Salesforce CRM Flow Configurations"
        ]
        prof_themes = [
            "SaaS Launch Strategy & Analytics", "ERP Deployment Compliance Audit",
            "CI/CD QA Verification Gateways", "QA Capstone System Deliverable"
        ]
        cert_name = "Professional Scrum Product Owner"
        cert_provider = "Scrum.org"
    elif track_type == "hardware_ece":
        beginner_themes = [
            "DC Circuits & Ohm's Law Essentials", "Digital Logic Design & Logic Gates",
            "Electronic Devices & Diodes/BJTs", "Circuit Simulation with SPICE Tools",
            "Microcontrollers & Arduino Coding", "Oscilloscopes & Lab Measurements"
        ]
        inter_themes = [
            "Analog Circuits & Op-Amp Systems", "Signals & Systems Fourier Analysis",
            "Verilog HDL & FPGA Implementations", "Embedded C & ARM Cortex Architecture",
            "Printed Circuit Board (PCB) Layouts", "Sensors & Actuators Integrations"
        ]
        adv_themes = [
            "VLSI Design & CMOS Technologies", "Digital Signal Processing (DSP) Filters",
            "Power Electronics & Converter Design", "Embedded RTOS & Multi-Threading",
            "Wireless Communication & RF Circuits"
        ]
        prof_themes = [
            "ASIC Design Flows & Tape-Out Audits", "EMI/EMC Compliance & Thermal Controls",
            "IoT Firmware Security & OTA Updates", "Production Capstone Hardware System"
        ]
        cert_name = "IEEE Certified Electronics Specialist"
        cert_provider = "IEEE"
    elif track_type == "csbs":
        beginner_themes = [
            "Cell Biology & Molecular Genetics Basics", "Python Programming & Biopython Libraries",
            "Introduction to Bioinformatics Databases", "Sequence Alignment & FASTA File Formats",
            "Biostatistics & Normal Distributions", "Intro to Genomics & DNA Sequencing"
        ]
        inter_themes = [
            "Dynamic Programming Sequence Alignment", "Phylogenetic Tree Reconstruction Methods",
            "Structural Biology & 3D Protein Viewing", "Gene Expression Profiling & RNA-Seq",
            "Machine Learning for Biomarker Detection", "Pathway Enrichment & Reactome Analysis"
        ]
        adv_themes = [
            "Deep Learning for Protein Fold Prediction", "Metagenomics & Microbial Ecology Pipelines",
            "Genome Assembly & Variant Calling Flows", "Computational Drug Design & Molecular Docking",
            "Vector Databases for Biomedical Literature"
        ]
        prof_themes = [
            "Clinical Trials Data Compliance & HIPAA", "Production Pipeline for Genomic Analytics",
            "Cloud Platforms for Big Biotech Data", "Biotech Capstone Model Implementation"
        ]
        cert_name = "Bioinformatics Specialist Certification"
        cert_provider = "ISCB"
    elif track_type == "traditional_eng":
        beginner_themes = [
            "Engineering Mathematics & Physics", "Engineering Mechanics & Statics",
            "Introduction to CAD & 2D Drafting", "Thermodynamics & Heat Transfer Basics",
            "Materials Science & Fluid Mechanics", "Engineering Chemistry Essentials"
        ]
        inter_themes = [
            "3D Solid Modeling & CAD Software", "Finite Element Analysis (FEA) Basics",
            "Manufacturing Processes & Tooling", "Structural Analysis & Concrete Design",
            "Chemical Reaction Engineering Principles", "Hydraulics & Pneumatic Control Systems"
        ]
        adv_themes = [
            "Computational Fluid Dynamics (CFD)", "Geotechnical & Foundation Engineering",
            "Chemical Process Simulation & Tools", "Automotive Systems & Powertrains",
            "Dynamic Systems & Kinematics Control"
        ]
        prof_themes = [
            "Industrial Plant Design Operations", "Project Estimation & Cost Audits",
            "HVAC Systems & Environmental Safety", "Engineering Capstone System Project"
        ]
        cert_name = "Professional Engineer (PE) License Prep"
        cert_provider = "NCEES"
    elif track_type == "quantum":
        beginner_themes = [
            "Dirac Notation & Quantum States", "Quantum Superposition Principle",
            "Bloch Sphere Geometry & Operations", "Quantum Logic Gates (H, X, Y, Z, CNOT)",
            "Qiskit Framework Setup & SDK", "Quantum Circuit Simulation Basics"
        ]
        inter_themes = [
            "Quantum Entanglement & EPR Pairs", "Bell States & Quantum Teleportation",
            "Quantum Fourier Transform (QFT)", "Quantum Phase Estimation Algorithm",
            "Deutsch-Jozsa & Bernstein-Vazirani Algorithms", "Quantum SDK Circuit Execution"
        ]
        adv_themes = [
            "Shor's Integer Factoring Algorithm", "Grover's Database Search Algorithm",
            "Quantum Error Correction (QEC) Basics", "Variational Quantum Eigensolver (VQE)",
            "Quantum Approximation Optimization Algorithm (QAOA)"
        ]
        prof_themes = [
            "Superconducting Qubits & Hardware", "Quantum Key Distribution (QKD) Protocols",
            "Quantum Chemistry Simulations", "Quantum Machine Learning (QML) Capstone"
        ]
        cert_name = "IBM Certified Associate Developer: Quantum Computation"
        cert_provider = "IBM"
    else: # dev / Full Stack
        beginner_themes = [
            "HTTP Protocols & Web Architectures", "Semantic HTML5 Page Layouts",
            "CSS Flexbox & Page Grids Layout", "Responsive CSS Variables & MQ",
            "JavaScript Arrays & Page Events", "Promises & Async Fetch Calls"
        ]
        inter_themes = [
            "React Functional Page Components", "React hooks state management",
            "Node.js & Express REST APIs Routing", "Database Relational Schemas",
            "SQL Queries and indexing optimizations", "JWT Authentication and session security"
        ]
        adv_themes = [
            "Redux Global State Management", "WebSockets Real-Time Communications",
            "Dockerizing Full Stack Server Layers", "Continuous Integration pipelines",
            "Redis Output Query Memory Caching"
        ]
        prof_themes = [
            "Microservices Cloud Deployment Plans", "Automated Visual Test Frameworks",
            "Zero-Downtime Release CD Scripts", "Capstone Web SaaS Deployment"
        ]
        cert_name = "Meta Full-End Certificate"
        cert_provider = "Meta"

    # Assemble 200 nodes!
    nodes = []
    for i in range(1, 201):
        if i <= 50:
            diff = "BEGINNER"
            theme = beginner_themes[(i - 1) % len(beginner_themes)]
            subtopic = f"Topic {i}: foundational exploration of {theme} tools."
            why = f"Essential for setting up baseline developer skills in {role}."
            dur = "4 hours"
            reward = 25
            proj = "Foundational Task Checkpoint"
            tasks = ["Set up dev environment", "Write code syntax tests", "Verify log output"]
        elif i <= 120:
            diff = "INTERMEDIATE"
            theme = inter_themes[(i - 51) % len(inter_themes)]
            subtopic = f"Topic {i}: intermediate implementation of {theme} frameworks."
            why = f"Required to build functional mid-tier applications and configure {role} systems."
            dur = "8 hours"
            reward = 50
            proj = "Intermediate Level Mock Application"
            tasks = ["Configure database models", "Write integration tests", "Deploy mock container"]
        elif i <= 170:
            diff = "ADVANCED"
            theme = adv_themes[(i - 121) % len(adv_themes)]
            subtopic = f"Topic {i}: advanced optimizations of {theme} design patterns."
            why = f"Equips you to optimize scale, concurrency, and security in {role} deployments."
            dur = "12 hours"
            reward = 75
            proj = "Advanced Optimizations Project"
            tasks = ["Configure load balancer", "Write benchmark assertions", "Perform load tests"]
        else:
            diff = "PROFESSIONAL"
            theme = prof_themes[(i - 171) % len(prof_themes)]
            subtopic = f"Topic {i}: production launch and audits of {theme} systems."
            why = f"Prepares you for real-world enterprise architectures and certifications matching {role} roles."
            dur = "16 hours"
            reward = 100
            proj = "Production Capstone Deployment"
            tasks = ["Configure ArgoCD GitOps sync", "Run Trivy container scan", "Execute chaos testing"]
            
        nodes.append({
            "id": f"node-{i}",
            "title": f"Step {i}: {theme} Checkpoint",
            "description": subtopic,
            "difficulty": diff,
            "estimated_duration": dur,
            "why_learn_it": why,
            "prerequisites": f"Step {i-1}" if i > 1 else "None",
            "xp_reward": reward,
            "resources": [
                {"title": f"GeeksforGeeks: {theme} Reference Guide", "url": f"https://www.geeksforgeeks.org/search-results/?q={theme.lower().replace(' ', '+')}"},
                {"title": f"YouTube: {theme} Full Course Playlist", "url": f"https://www.youtube.com/results?search_query={theme.lower().replace(' ', '+')}+tutorial"},
                {"title": f"W3Schools: Learn {theme} Interactive Tutorial", "url": "https://www.w3schools.com"},
                {"title": f"freeCodeCamp: {theme} Complete Guide", "url": "https://www.freecodecamp.org"},
                {"title": f"LeetCode: {theme} Programming Challenges", "url": "https://leetcode.com/problemset/all/"},
                {"title": f"HackerRank: {theme} Skill Practice", "url": "https://www.hackerrank.com"},
                {"title": f"Google Search: {theme} Best Practices", "url": f"https://www.google.com/search?q={theme.lower().replace(' ', '+')}+best+practices"},
                {"title": f"Dev.to: {theme} Community Blogs & Articles", "url": f"https://dev.to/t/{theme.lower().replace(' ', '')}"},
                {"title": f"Medium: {theme} Architectural Patterns", "url": "https://medium.com"},
                {"title": f"Coursera: {theme} Specialization Courses", "url": "https://www.coursera.org"},
                {"title": f"Udemy: {theme} Development Video Lectures", "url": "https://www.udemy.com"},
                {"title": f"Khan Academy: {theme} Analytical Foundations", "url": "https://www.khanacademy.org"},
                {"title": f"Tutorialspoint: {theme} Easy Tutorials", "url": "https://www.tutorialspoint.com"},
                {"title": f"StackOverflow: {theme} Debugging FAQ", "url": f"https://stackoverflow.com/questions/tagged/{theme.lower().replace(' ', '-')}"},
                {"title": f"GitHub Search: {theme} Open Source Repos", "url": f"https://github.com/search?q={theme.lower().replace(' ', '+')}"}
            ],
            "projects": [{
                "title": f"Step {i} Practice Project: {proj}",
                "description": f"Design and implement a structured module targeting {theme}.",
                "tasks": tasks
            }],
            "certifications": [{
                "name": cert_name,
                "provider": cert_provider,
                "cost": "$99-$165",
                "duration": "2 hours exam",
                "difficulty": diff,
                "career_impact": "High demand, unlocks recruiter screening filters."
            }],
            "interview_questions": [
                {"question": f"What is the primary role of {theme} in industry systems?", "answer": f"{theme} helps organize, build, and optimize backend or frontend systems by following modern software standards."},
                {"question": f"Explain one common pitfall or vulnerability when dealing with {theme}.", "answer": f"Misconfiguration, lack of sanitization, or unoptimized complexity in {theme} can lead to severe bottlenecks and data risks."},
                {"question": f"Name three tools commonly used to develop, test, or deploy {theme}.", "answer": f"Typical developer workflows include Git, VS Code, and container tools like Docker for managing {theme} code."},
                {"question": f"How does scaling impact {theme} architectures?", "answer": f"Horizontal scaling, database sharding, and caching help reduce latency as user requests scale in {theme} modules."},
                {"question": f"What is a standard best practice for monitoring {theme}?", "answer": f"Implement structured logs, index metrics in dashboards, and setup alert thresholds for anomalies in {theme} services."},
                {"question": f"How do you handle unit testing and verification for {theme} logic?", "answer": f"Write mock tests to verify core algorithms, assertions on inputs/outputs, and automate checking within CI pipelines for {theme}."},
                {"question": f"What is the security risk associated with misconfigured {theme}?", "answer": f"Improper permissions, lack of sanitization, or exposed endpoints in {theme} can lead to data leaks or remote code execution."},
                {"question": f"Differentiate between synchronous and asynchronous operations in {theme}.", "answer": f"Synchronous blocks execution until {theme} tasks complete, while asynchronous operations run in the background via callbacks or promises."},
                {"question": f"How does caching optimize workflows involving {theme}?", "answer": f"Caching stores frequent query results of {theme} in memory (like Redis), reducing database hits and resource consumption."},
                {"question": f"Describe how you would design a logging strategy for debugging {theme} in production.", "answer": f"Log key {theme} execution events, error stack traces, execution duration, and log severity levels (INFO, WARN, ERROR) to central indexers."},
                {"question": f"What performance metrics are most critical to monitor for {theme}?", "answer": f"Response latency of {theme} calls, throughput (requests per second), memory utilization, and CPU load."}
            ]
        })
        
    return nodes

# --- ROUTES CONTROLLERS ---

# 1. Learning Roadmaps
@features_bp.route('/roadmaps', methods=['GET'])
@login_required
def list_roadmaps():
    try:
        # Load user active track
        progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
        
        tracks = [
            "Cyber Security", "Ethical Hacking", "SOC Analyst", "Digital Forensics",
            "AI Engineering", "Machine Learning", "Deep Learning", "Generative AI", "Prompt Engineering", "Agentic AI",
            "Data Science", "Data Analytics", "Python Developer", "Java Developer", "C++ Developer",
            "Full Stack Development", "Frontend Development", "Backend Development", "React Developer", "Node.js Developer",
            "Mobile App Development", "Android Development", "Flutter Development",
            "Cloud Computing", "AWS", "Azure", "Google Cloud",
            "DevOps", "Kubernetes", "Docker", "Linux Engineering", "Network Engineering",
            "Blockchain", "Web3", "UI/UX Design", "Product Design", "Product Management",
            "Software Testing", "QA Automation", "Game Development", "AR/VR Development",
            "Robotics & Automation", "IoT", "Embedded Systems", "Embedded Systems and Electronics", "Database Engineering",
            "Site Reliability Engineering", "Business Analysis", "SAP", "Salesforce", "Competitive Programming",
            "VLSI Design", "Electronics & Communication (ECE)", "Electrical Engineering",
            "Power Systems Engineering", "Computer Science & Bio Science (CSBS)",
            "Mechanical Engineering", "Civil Engineering", "Chemical Engineering",
            "Data Engineering", "Biotechnology", "Quantum Computing Engineering",
            "Aerospace Engineering", "Automotive Engineering", "Renewable Energy Engineering",
            "Nuclear Engineering", "Marine Engineering", "Environmental Engineering",
            "Materials Science & Engineering", "Bio-Medical Engineering"
        ]
        
        selected_role = None
        nodes = []
        completed_set = set()
        percent = 0
        
        if progress:
            selected_role = progress.role
            nodes = get_predefined_roadmap(selected_role)
            if progress.completed_nodes:
                completed_set = {int(x) for x in progress.completed_nodes.split(",") if x.strip()}
            
            completed_count = len([n for i, n in enumerate(nodes) if (i+1) in completed_set])
            if nodes:
                percent = int((completed_count / len(nodes)) * 100)
                
        return render_template(
            'roadmaps.html', 
            tracks=tracks, 
            selected_role=selected_role,
            nodes=nodes, 
            completed_set=completed_set,
            percent=percent
        )
    except Exception as e:
        print(f"Error in list_roadmaps: {e}")
        flash("An error occurred loading your roadmap. Please try again.", "danger")
        return render_template('roadmaps.html', tracks=[], selected_role=None, nodes=[], completed_set=set(), percent=0)

@features_bp.route('/roadmaps/select-track', methods=['POST'])
@login_required
def select_track():
    track_name = request.form.get('track')
    if not track_name:
        flash("Invalid track selection.", "danger")
        return redirect(url_for('features.list_roadmaps'))
        
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    if not progress:
        progress = RoadmapProgress(user_id=current_user.id, role=track_name, completed_nodes="")
        db.session.add(progress)
    else:
        progress.role = track_name
        progress.completed_nodes = ""
    db.session.commit()
    
    flash(f"Generated visual pathway for {track_name}!", "success")
    return redirect(url_for('features.list_roadmaps'))

@features_bp.route('/roadmaps/toggle-step', methods=['POST'])
@login_required
def toggle_step():
    data = request.get_json() or {}
    step_num = data.get('step')
    if step_num is None:
        return jsonify({"success": False, "error": "Step number required"}), 400
        
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    if not progress:
        return jsonify({"success": False, "error": "No active roadmap found"}), 400
        
    completed_list = [int(x) for x in progress.completed_nodes.split(",") if x.strip()]
    if step_num in completed_list:
        completed_list.remove(step_num)
        status = "removed"
    else:
        completed_list.append(step_num)
        status = "added"
        
    progress.completed_nodes = ",".join(str(x) for x in sorted(completed_list))
    
    # Calculate XP reward
    if step_num <= 50:
        reward = 25
    elif step_num <= 120:
        reward = 50
    elif step_num <= 170:
        reward = 75
    else:
        reward = 100
        
    if status == "added":
        current_user.xp += reward
        current_user.learning_streak = (current_user.learning_streak or 0) + 1
    else:
        current_user.xp = max(0, current_user.xp - reward)
        current_user.learning_streak = max(0, (current_user.learning_streak or 1) - 1)
        
    db.session.commit()
    
    # Calculate new percentage
    nodes = get_predefined_roadmap(progress.role)
    completed_count = len([n for i, n in enumerate(nodes) if (i+1) in completed_list])
    percent = int((completed_count / len(nodes)) * 100) if nodes else 0
    
    return jsonify({
        "success": True, 
        "status": status, 
        "percent": percent,
        "completed_count": completed_count,
        "total_count": len(nodes),
        "xp": current_user.xp,
        "streak": current_user.learning_streak
    })


# 2. ATS Resume Analyzer
@features_bp.route('/resume-analyzer', methods=['GET'])
@login_required
def resume_analyzer():
    history = ResumeAnalysis.query.filter_by(user_id=current_user.id).order_by(ResumeAnalysis.created_at.desc()).all()
    # Parse the analysis details JSON of the latest record
    latest = None
    if history:
        latest = history[0]
        try:
            latest.details = json.loads(latest.analysis_json)
        except Exception:
            latest.details = {}
            
    return render_template('resume_analyzer.html', history=history, latest=latest)

@features_bp.route('/resume-analyzer/upload', methods=['POST'])
@login_required
def upload_resume():
    file = request.files.get('resume_file')
    custom_key = (request.form.get('custom_key') or '').strip()
    
    if not file or file.filename == '':
        return jsonify({"success": False, "error": "No file uploaded"}), 400
        
    filename = file.filename
    file_bytes = file.read()
    extracted_text = ""
    
    try:
        if filename.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_bytes)
        elif filename.lower().endswith('.docx'):
            extracted_text = extract_text_from_docx(file_bytes)
        else:
            return jsonify({"success": False, "error": "Unsupported file format. Use PDF or DOCX."}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to parse file: {str(e)}"}), 500
        
    if not extracted_text:
        return jsonify({"success": False, "error": "No readable text extracted."}), 400
        
    # Check for AI key (User provided, DB global, or Env)
    from app.models import SiteConfig
    api_key = custom_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY") or SiteConfig.get('global_ai_key', '')
    
    fields = None
    analysis = None
    
    if api_key:
        parser_system_prompt = (
            "You are a recruitment database parser. Extract details from the resume text into the following JSON format:\n"
            "{\n"
            "  \"name\": \"...\",\n"
            "  \"address\": \"...\",\n"
            "  \"email\": \"...\",\n"
            "  \"phone\": \"...\",\n"
            "  \"linkedin\": \"...\",\n"
            "  \"github\": \"...\",\n"
            "  \"portfolio\": \"...\",\n"
            "  \"edu1Inst\": \"...\",\n"
            "  \"edu1Degree\": \"...\",\n"
            "  \"edu1Dates\": \"...\",\n"
            "  \"edu1Gpa\": \"...\",\n"
            "  \"edu1Coursework\": \"...\",\n"
            "  \"skillsProg\": \"...\",\n"
            "  \"skillsCyber\": \"...\",\n"
            "  \"skillsTools\": \"...\",\n"
            "  \"skillsWeb\": \"...\",\n"
            "  \"experienceRole\": \"...\",\n"
            "  \"experienceComp\": \"...\",\n"
            "  \"experienceDates\": \"...\",\n"
            "  \"experienceB1\": \"...\",\n"
            "  \"experienceB2\": \"...\",\n"
            "  \"experienceB3\": \"...\",\n"
            "  \"experienceB4\": \"...\",\n"
            "  \"projectTitle\": \"...\",\n"
            "  \"projectLink\": \"...\",\n"
            "  \"projectB1\": \"...\",\n"
            "  \"projectB2\": \"...\",\n"
            "  \"projectB3\": \"...\",\n"
            "  \"certC1\": \"...\",\n"
            "  \"certC2\": \"...\",\n"
            "  \"certC3\": \"...\",\n"
            "  \"certC4\": \"...\",\n"
            "  \"achievements\": \"...\",\n"
            "  \"hackathons\": \"...\",\n"
            "  \"workshops\": \"...\",\n"
            "  \"volunteering\": \"...\",\n"
            "  \"languages\": \"...\",\n"
            "  \"interests\": \"...\",\n"
            "  \"references\": \"...\",\n"
            "  \"custom\": \"...\"\n"
            "}\n"
            "Ensure everything is returned as a plain JSON object without any additional conversational text or markdown wrappers."
        )
        try:
            parsed_res = call_gemini(parser_system_prompt, extracted_text, user_key=api_key)
            if parsed_res:
                json_match = re.search(r'\{.*\}', parsed_res, re.DOTALL)
                if json_match:
                    fields = json.loads(json_match.group(0))
        except Exception as e:
            print(f"Failed to parse resume using AI: {e}")

        ats_system_prompt = (
            "You are an expert ATS (Applicant Tracking System) Resumes Auditor. Analyze the resume text and provide a structured audit in JSON format.\n"
            "The JSON must have these exact keys:\n"
            "- \"atsScore\": integer 0 to 100\n"
            "- \"formattingScore\": integer 0 to 100\n"
            "- \"skillsScore\": integer 0 to 100\n"
            "- \"keywordScore\": integer 0 to 100\n"
            "- \"readabilityScore\": integer 0 to 100\n"
            "- \"projectQualityScore\": integer 0 to 100\n"
            "- \"missingKeywords\": list of strings\n"
            "- \"improvements\": list of objects, each with \"originalText\", \"suggestedText\", \"reason\"\n"
            "- \"mistakes\": list of strings\n"
            "- \"suggestions\": list of strings\n\n"
            "Return only the valid JSON block without markdown wrappers or extra text."
        )
        try:
            analysis_res = call_gemini(ats_system_prompt, extracted_text, user_key=api_key)
            if analysis_res:
                json_match = re.search(r'\{.*\}', analysis_res, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group(0))
        except Exception as e:
            print(f"Failed to analyze resume using AI: {e}")

    # Fallbacks to heuristics
    if not fields:
        fields = parse_text_to_resume_fields(extracted_text)
    if not analysis:
        analysis = heuristic_parse_resume(extracted_text)
        
    # Ensure all scores exist with default heuristics if missing from AI
    formatting = analysis.get('formattingScore') or analysis.get('formatting')
    if formatting is None:
        formatting = min(100, 70 + (10 if fields.get('email') else 0) + (10 if fields.get('phone') else 0) + (10 if fields.get('github') or fields.get('linkedin') else 0))
    analysis['formattingScore'] = formatting

    skills = analysis.get('skillsScore') or analysis.get('skills') or analysis.get('industryMatchScore') or 75
    analysis['skillsScore'] = skills

    keyword = analysis.get('keywordScore') or analysis.get('keyword') or analysis.get('industryMatchScore') or 75
    analysis['keywordScore'] = keyword

    readability = analysis.get('readabilityScore') or analysis.get('readability') or 75
    analysis['readabilityScore'] = readability

    projects = analysis.get('projectQualityScore') or analysis.get('projectQuality') or 75
    analysis['projectQualityScore'] = projects

    new_analysis = ResumeAnalysis(
        user_id=current_user.id,
        filename=filename,
        ats_score=analysis['atsScore'],
        readability_score=analysis['readabilityScore'],
        industry_match_score=analysis.get('industryMatchScore', 75),
        target_role="Software Engineer",
        analysis_json=json.dumps(analysis)
    )
    db.session.add(new_analysis)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": fields,
        "score": analysis['atsScore'],
        "formatting": formatting,
        "skills": skills,
        "keyword": keyword,
        "readability": readability,
        "projects": projects,
        "alignment": analysis.get('industryMatchScore', 75),
        "feedback": {
            "score": analysis['atsScore'],
            "formatting": formatting,
            "skills": skills,
            "keyword": keyword,
            "readability": readability,
            "projects": projects,
            "missingKeywords": analysis.get('missingKeywords', []),
            "improvements": analysis.get('improvements', []),
            "mistakes": analysis.get('mistakes', []),
            "suggestions": analysis.get('suggestions', [])
        }
    })

@features_bp.route('/resume-analyzer/save-version', methods=['POST'])
@login_required
def save_resume_version():
    data = request.get_json() or {}
    title = data.get('title', 'My Draft Resume')
    theme = data.get('theme', 'classic')
    content = data.get('content', {})
    ats_score = data.get('ats_score', 0)
    
    # Check if a resume with this title already exists for the user
    resume = UserResume.query.filter_by(user_id=current_user.id, title=title).first()
    if resume:
        resume.theme = theme
        resume.content_json = json.dumps(content)
        resume.ats_score = ats_score
        resume.updated_at = datetime.utcnow()
    else:
        resume = UserResume(
            user_id=current_user.id,
            title=title,
            theme=theme,
            content_json=json.dumps(content),
            ats_score=ats_score
        )
        db.session.add(resume)
        
    db.session.commit()
    return jsonify({"success": True, "message": "Resume version saved successfully!"})

@features_bp.route('/resume-analyzer/versions', methods=['GET'])
@login_required
def list_resume_versions():
    resumes = UserResume.query.filter_by(user_id=current_user.id).order_by(UserResume.updated_at.desc()).all()
    results = []
    for r in resumes:
        try:
            content = json.loads(r.content_json)
        except Exception:
            content = {}
        results.append({
            "id": r.id,
            "title": r.title,
            "theme": r.theme,
            "ats_score": r.ats_score,
            "content": content,
            "updated_at": r.updated_at.strftime('%Y-%m-%d %H:%M')
        })
    return jsonify({"success": True, "versions": results})

# 3. Smart AI Actions
@features_bp.route('/smart-ai/study-plan', methods=['POST'])
@login_required
def generate_study_plan():
    try:
        from app.models import SiteConfig
        data = request.get_json() or {}
        custom_key = (data.get('custom_key') or '').strip()
        if not custom_key:
            custom_key = SiteConfig.get('global_ai_key', '') or ''

        branch = current_user.branch or "Computer Science"
        year = current_user.year or "3rd Year"
        goal = current_user.career_goal or "Software Engineering"
        skills = current_user.skills or "Python, HTML/CSS, SQL"

        system_prompt = (
            "You are a professional Academic Curriculum Director and Study Coach. "
            "Your task is to generate a highly structured, week-by-week study plan (for next 12 weeks) "
            "designed to help a student transition from their current status to their target career path.\n\n"
            "Format the output in clean, professional Markdown with subheadings for each week. "
            "Include weekly goals, study hour suggestions, key conceptual topics, practice coding exercises, "
            "and project milestones. Keep it actionable and tailored to the student's constraints."
        )
        user_prompt = (
            f"Student Profile:\n"
            f"- Academic Major/Branch: {branch}\n"
            f"- Current Year: {year}\n"
            f"- Target Career Role: {goal}\n"
            f"- Known Technical Skills: {skills}\n"
            f"- Target Study Budget: {current_user.daily_study_time or '2 hours/day'}"
        )

        ai_res = call_gemini(system_prompt, user_prompt, user_key=custom_key)
        if not ai_res:
            ai_res = (
                f"### 12-Week AI Study Plan: {goal}\n\n"
                f"* **Week 1-4: Core Technical Pillars**\n"
                f"  - Focus: Refresh {skills}. Master basic data structures and system architecture components.\n"
                f"  - Hours: Allocate 2 hours/day.\n"
                f"* **Week 5-8: Intermediate Project Engineering**\n"
                f"  - Focus: Start designing a custom portfolio project. Integrate SQL/NoSQL database layers.\n"
                f"* **Week 9-12: System Scaling & Placement Preparation**\n"
                f"  - Focus: Configure deployment configurations (Docker, CI/CD) and solve active LeetCode topics.\n\n"
                f"*(Note: Configure your Groq/Gemini key in Settings to unlock deep customized AI plans!)*"
            )

        return jsonify({"success": True, "study_plan": ai_res})
    except Exception as e:
        print(f"Error generating study plan: {e}")
        return jsonify({"success": False, "error": "Server error while generating study plan."}), 500


@features_bp.route('/smart-ai/internship-readiness', methods=['POST'])
@login_required
def generate_internship_readiness():
    try:
        from app.models import SiteConfig
        data = request.get_json() or {}
        custom_key = (data.get('custom_key') or '').strip()
        if not custom_key:
            custom_key = SiteConfig.get('global_ai_key', '') or ''

        branch = current_user.branch or "Computer Science"
        year = current_user.year or "3rd Year"
        goal = current_user.career_goal or "Software Engineering"
        skills = current_user.skills or "Python, HTML/CSS, SQL"
        
        # Read latest resume analysis
        resume = ResumeAnalysis.query.filter_by(user_id=current_user.id).order_by(ResumeAnalysis.created_at.desc()).first()
        resume_score = resume.ats_score if resume else 0

        system_prompt = (
            "You are an ATS Recruitment Architect and Career Placement Director. "
            "Analyze the student's profile and resume score, and output a detailed Internship Readiness Report in JSON format.\n"
            "The JSON must contain exactly 5 keys:\n"
            "- \"score\": a calculated integer rating (0 to 100) representing how ready the student is for a high-paying internship.\n"
            "- \"missing_skills\": a list of 3-5 critical technical skills or keywords missing from the student's skill inventory.\n"
            "- \"missing_certs\": a list of 2-3 industry certifications that would maximize recruiter matches.\n"
            "- \"missing_projects\": a list of 2-3 advanced project architectures the student should build next.\n"
            "- \"action_plan\": a detailed, step-by-step action plan in Markdown format containing immediate tasks to improve matching rates.\n\n"
            "Return ONLY the valid JSON block without any extra text wrapper or markdown markers."
        )
        user_prompt = (
            f"Student Details:\n"
            f"- Branch: {branch}, Year: {year}\n"
            f"- Target Career Path: {goal}\n"
            f"- Known Skills: {skills}\n"
            f"- Current Resume ATS Compatibility Score: {resume_score}/100"
        )

        ai_res = call_gemini(system_prompt, user_prompt, user_key=custom_key)
        
        # Default mock parser fallback
        score = 65
        missing_skills = ["Docker", "Kubernetes", "Linux Hardening", "System Design"]
        missing_certs = ["AWS Certified Developer", "CompTIA Security+"]
        missing_projects = ["Multi-tier Microservices App", "CI/CD Pipeline Automation"]
        action_plan = (
            "1. **Core Skills Expansion**: Add containerization (Docker) to your skill list by containerizing a mock web app.\n"
            "2. **Resume Polish**: Improve your resume summary with specific quantitative achievements (e.g. 'Reduced latency by 25%').\n"
            "3. **Milestone Targets**: Complete the remaining learning roadmap modules to reach at least 80% completion."
        )

        if ai_res:
            try:
                json_match = re.search(r'\{.*\}', ai_res, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    score = parsed.get('score', score)
                    missing_skills = parsed.get('missing_skills', missing_skills)
                    missing_certs = parsed.get('missing_certs', missing_certs)
                    missing_projects = parsed.get('missing_projects', missing_projects)
                    action_plan = parsed.get('action_plan', action_plan)
            except Exception as e:
                print(f"Error parsing AI readiness JSON: {e}")
                
        return jsonify({
            "success": True,
            "score": score,
            "missing_skills": missing_skills,
            "missing_certs": missing_certs,
            "missing_projects": missing_projects,
            "action_plan": action_plan
        })
    except Exception as e:
        print(f"Error generating readiness report: {e}")
        return jsonify({"success": False, "error": "Server error while calculating readiness."}), 500


@features_bp.route('/smart-ai/certification-plan', methods=['POST'])
@login_required
def generate_certification_plan():
    try:
        from app.models import SiteConfig
        data = request.get_json() or {}
        custom_key = (data.get('custom_key') or '').strip()
        if not custom_key:
            custom_key = SiteConfig.get('global_ai_key', '') or ''

        branch = current_user.branch or "Computer Science"
        year = current_user.year or "3rd Year"
        goal = current_user.career_goal or "Software Engineering"
        skills = current_user.skills or "Python, HTML/CSS, SQL"

        system_prompt = (
            "You are a Professional Certification Specialist and Career Matcher. "
            "For the student's profile, recommend exactly 3 highly valued industry certifications.\n"
            "Output your recommendation in JSON format containing exactly 1 key:\n"
            "- \"certifications\": a list of 3 objects, where each object has keys:\n"
            "  * \"name\": name of the certification (e.g. AWS Certified Developer - Associate)\n"
            "  * \"provider\": provider name (e.g. Amazon Web Services)\n"
            "  * \"hours\": estimated prep time (e.g. 80 hours)\n"
            "  * \"difficulty\": Beginner, Intermediate, or Advanced\n"
            "  * \"cost\": estimated exam cost (e.g. $150 USD)\n"
            "  * \"value\": a short description of why it is extremely valuable for this target career role.\n\n"
            "Return ONLY the valid JSON block without any extra text wrappers or markdown tags."
        )
        user_prompt = (
            f"Student Details:\n"
            f"- Branch: {branch}, Year: {year}\n"
            f"- Goal Career: {goal}\n"
            f"- Current Skills: {skills}"
        )

        ai_res = call_gemini(system_prompt, user_prompt, user_key=custom_key)
        
        certs = [
            {
                "name": "AWS Certified Solutions Architect - Associate",
                "provider": "Amazon Web Services",
                "hours": "80-120 hours",
                "difficulty": "Intermediate",
                "cost": "$150 USD",
                "value": "Validates broad knowledge of cloud networking, security groups, and microservices databases architectures."
            },
            {
                "name": "CompTIA Security+",
                "provider": "CompTIA",
                "hours": "60-80 hours",
                "difficulty": "Beginner",
                "cost": "$392 USD",
                "value": "Core baseline certification mapping standard networks threat profiles, cryptography hashing protocols, and security audits."
            },
            {
                "name": "Microsoft Certified: Azure Developer Associate",
                "provider": "Microsoft",
                "hours": "70-90 hours",
                "difficulty": "Intermediate",
                "cost": "$165 USD",
                "value": "Validates ability to design, build, test, and maintain cloud applications and services on Microsoft Azure."
            }
        ]

        if ai_res:
            try:
                json_match = re.search(r'\{.*\}', ai_res, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    certs = parsed.get('certifications', certs)
            except Exception as e:
                print(f"Error parsing AI certs JSON: {e}")

        return jsonify({"success": True, "certifications": certs})
    except Exception as e:
        print(f"Error generating certification plan: {e}")
        return jsonify({"success": False, "error": "Server error while generating certification plan."}), 500

# 4. AJAX Resume Analysis (Side-by-side Builder Verification)
@features_bp.route('/resume-analyzer/analyze', methods=['POST'])
@login_required
def analyze_resume_ajax():
    data = request.get_json() or {}
    custom_key = (data.get('custom_key') or '').strip()
    
    name = data.get('name', '')
    email = data.get('email', '')
    phone = data.get('phone', '')
    github = data.get('github', '')
    linkedin = data.get('linkedin', '')
    skills = f"{data.get('skillsProg', '')} {data.get('skillsCyber', '')} {data.get('skillsOs', '')} {data.get('skillsTools', '')} {data.get('skillsWeb', '')}"
    experience = f"{data.get('experienceRole', '')} {data.get('experienceComp', '')} {data.get('experienceB1', '')} {data.get('experienceB2', '')} {data.get('experienceB3', '')} {data.get('experienceB4', '')}"
    projects = f"{data.get('projectTitle', '')} {data.get('projectB1', '')} {data.get('projectB2', '')} {data.get('projectB3', '')}"
    certs = f"{data.get('certC1', '')} {data.get('certC2', '')} {data.get('certC3', '')} {data.get('certC4', '')}"
    
    full_text = f"{name}\n{email}\n{phone}\n{github}\n{linkedin}\n{skills}\n{experience}\n{projects}\n{certs}"
    
    # Check for AI key (User provided, DB global, or Env)
    from app.models import SiteConfig
    api_key = custom_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY") or SiteConfig.get('global_ai_key', '')
    
    analysis = None
    
    if api_key:
        ats_system_prompt = (
            "You are an expert ATS (Applicant Tracking System) Resumes Auditor. Analyze the resume text and provide a structured audit in JSON format.\n"
            "The JSON must have these exact keys:\n"
            "- \"atsScore\": integer 0 to 100\n"
            "- \"formattingScore\": integer 0 to 100\n"
            "- \"skillsScore\": integer 0 to 100\n"
            "- \"keywordScore\": integer 0 to 100\n"
            "- \"readabilityScore\": integer 0 to 100\n"
            "- \"projectQualityScore\": integer 0 to 100\n"
            "- \"missingKeywords\": list of strings\n"
            "- \"improvements\": list of objects, each with \"originalText\", \"suggestedText\", \"reason\"\n"
            "- \"mistakes\": list of strings\n"
            "- \"suggestions\": list of strings\n\n"
            "Return only the valid JSON block without markdown wrappers or extra text."
        )
        try:
            analysis_res = call_gemini(ats_system_prompt, full_text, user_key=api_key)
            if analysis_res:
                json_match = re.search(r'\{.*\}', analysis_res, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group(0))
        except Exception as e:
            print(f"Failed to analyze resume using AI: {e}")
            
    if not analysis:
        analysis = heuristic_parse_resume(full_text)
    
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    target_role = progress.role if progress else "Software Engineer"
    analysis['target_role'] = target_role

    # Ensure all scores exist with default heuristics if missing from AI
    formatting = analysis.get('formattingScore') or analysis.get('formatting')
    if formatting is None:
        formatting = min(100, 70 + (10 if email else 0) + (10 if phone else 0) + (10 if github or linkedin else 0))
    analysis['formattingScore'] = formatting

    skills = analysis.get('skillsScore') or analysis.get('skills') or analysis.get('industryMatchScore') or 75
    analysis['skillsScore'] = skills

    keyword = analysis.get('keywordScore') or analysis.get('keyword') or analysis.get('industryMatchScore') or 75
    analysis['keywordScore'] = keyword

    readability = analysis.get('readabilityScore') or analysis.get('readability') or 75
    analysis['readabilityScore'] = readability

    projects = analysis.get('projectQualityScore') or analysis.get('projectQuality') or 75
    analysis['projectQualityScore'] = projects
    
    new_analysis = ResumeAnalysis(
        user_id=current_user.id,
        filename=data.get('title', 'Scratch_Resume_Version'),
        ats_score=analysis['atsScore'],
        readability_score=analysis['readabilityScore'],
        industry_match_score=analysis.get('industryMatchScore', 75),
        target_role=target_role,
        analysis_json=json.dumps(analysis)
    )
    db.session.add(new_analysis)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "score": analysis['atsScore'],
        "formatting": formatting,
        "skills": skills,
        "keyword": keyword,
        "readability": readability,
        "projects": projects,
        "alignment": analysis.get('industryMatchScore', 75),
        "feedback": {
            "score": analysis['atsScore'],
            "formatting": formatting,
            "skills": skills,
            "keyword": keyword,
            "readability": readability,
            "projects": projects,
            "missingKeywords": analysis.get('missingKeywords', []),
            "improvements": analysis.get('improvements', []),
            "mistakes": analysis.get('mistakes', []),
            "suggestions": analysis.get('suggestions', [])
        }
    })

# 5. Interview Prep
@features_bp.route('/interview-prep', methods=['GET'])
@login_required
def interview_prep():
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    user_track = progress.role if progress else "Full Stack Development"
    
    tracks = [
        "Cyber Security", "Ethical Hacking", "SOC Analyst", "Digital Forensics",
        "AI Engineering", "Machine Learning", "Deep Learning", "Generative AI", "Prompt Engineering", "Agentic AI",
        "Data Science", "Data Analytics", "Python Developer", "Java Developer", "C++ Developer",
        "Full Stack Development", "Frontend Development", "Backend Development", "React Developer", "Node.js Developer",
        "Mobile App Development", "Android Development", "Flutter Development",
        "Cloud Computing", "AWS", "Azure", "Google Cloud",
        "DevOps", "Kubernetes", "Docker", "Linux Engineering", "Network Engineering",
        "Blockchain", "Web3", "UI/UX Design", "Product Design", "Product Management",
        "Software Testing", "QA Automation", "Game Development", "AR/VR Development",
        "Robotics & Automation", "IoT", "Embedded Systems", "Embedded Systems and Electronics", "Database Engineering",
        "Site Reliability Engineering", "Business Analysis", "SAP", "Salesforce", "Competitive Programming",
        "VLSI Design", "Electronics & Communication (ECE)", "Electrical Engineering",
        "Power Systems Engineering", "Computer Science & Bio Science (CSBS)",
        "Mechanical Engineering", "Civil Engineering", "Chemical Engineering",
        "Data Engineering", "Biotechnology", "Quantum Computing Engineering",
        "Aerospace Engineering", "Automotive Engineering", "Renewable Energy Engineering",
        "Nuclear Engineering", "Marine Engineering", "Environmental Engineering",
        "Materials Science & Engineering", "Bio-Medical Engineering"
    ]
    
    return render_template('interview_prep.html', user_track=user_track, tracks=tracks)

@features_bp.route('/interview-prep/evaluate', methods=['POST'])
@login_required
def interview_prep_evaluate():
    data = request.get_json() or {}
    question = data.get('question', '')
    answer = data.get('answer', '')
    custom_key = data.get('custom_key', '').strip()
    
    if not answer:
        return jsonify({"success": False, "error": "Answer is required"}), 400
        
    system_prompt = (
        "You are a Senior Technical Recruiter grading a mock coding/engineering interview. "
        "Analyze the candidate's answer for the technical question. "
        "Grade their answer out of 100, and provide clear constructive feedback. "
        "Provide your evaluation in JSON format with two keys: "
        "\"score\" (an integer from 0 to 100) and \"feedback\" (a detailed string summary)."
    )
    user_prompt = f"Question: {question}\nCandidate Answer: {answer}"
    
    ai_res = call_gemini(system_prompt, user_prompt, user_key=custom_key)
    score = 80
    feedback = "Good description of the concepts. Expand on practical edge cases."
    
    if ai_res:
        try:
            json_match = re.search(r'\{.*\}', ai_res, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                score = int(parsed.get('score', 80))
                feedback = parsed.get('feedback', ai_res)
            else:
                feedback = ai_res
        except Exception:
            feedback = ai_res
            
    return jsonify({
        "success": True,
        "score": score,
        "feedback": feedback
    })


# 7. Internship Center
@features_bp.route('/internship-center', methods=['GET'])
@login_required
def internship_center():
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    user_track = progress.role if progress else "Full Stack Development"
    
    db_internships = Internship.query.order_by(Internship.is_pinned.desc(), Internship.created_at.desc()).all()
    
    resume = ResumeAnalysis.query.filter_by(user_id=current_user.id).order_by(ResumeAnalysis.created_at.desc()).first()
    resume_score = resume.ats_score if resume else 0
    
    # Parse user skills
    user_skills_list = [s.strip().lower() for s in (current_user.skills or "").split(",") if s.strip()]
    
    # Calculate tech readiness score (completed nodes ratio)
    completed_nodes_count = 0
    if progress and progress.completed_nodes:
        completed_nodes_count = len([x for x in progress.completed_nodes.split(",") if x.strip()])
    tech_readiness = min(100, int((completed_nodes_count / 200) * 100)) if progress else 0
    
    # Fetch bookmarked items
    bookmarks = SavedItem.query.filter_by(user_id=current_user.id, item_type='internship').all()
    bookmarked_ids = {b.item_id for b in bookmarks}
    
    jobs = []
    for job in db_internships:
        # Parse job required skills
        req_skills = [s.strip() for s in (job.skills_required or "").split(",") if s.strip()]
        
        # Calculate matching & missing skills
        matched = [s for s in req_skills if s.lower() in user_skills_list]
        missing = [s for s in req_skills if s.lower() not in user_skills_list]
        
        compatibility = 30 if user_track.lower() in job.role.lower() or job.role.lower() in user_track.lower() else 10
        if req_skills:
            compatibility += int((len(matched) / len(req_skills)) * 40)
        compatibility += int((resume_score / 100) * 20)
        compatibility += int((tech_readiness / 100) * 10)
        compatibility = min(98, max(25, compatibility))
        
        # Determine recommended certifications based on role name
        role_lower = job.role.lower()
        if "cloud" in role_lower or "devops" in role_lower:
            recommended_certs = ["AWS Cloud Practitioner", "Docker Certified Associate"]
        elif "cyber" in role_lower or "security" in role_lower:
            recommended_certs = ["CompTIA Security+", "CEH (Ethical Hacker)"]
        elif "data" in role_lower or "analytics" in role_lower or "stats" in role_lower:
            recommended_certs = ["Google Data Engineer", "Microsoft Power BI Analyst"]
        elif "machine learning" in role_lower or " ml " in role_lower or "ai" in role_lower:
            recommended_certs = ["TensorFlow Developer Cert", "AWS ML Specialty"]
        elif "front" in role_lower or "web" in role_lower or "react" in role_lower or "ui" in role_lower or "ux" in role_lower:
            recommended_certs = ["Meta Front-End Developer", "Google UX Design"]
        else:
            recommended_certs = ["AWS Cloud Practitioner", "Microsoft Azure Fundamentals"]

        resume_match = min(98, max(25, int(compatibility * 1.05)))

        jobs.append({
            "id": job.id,
            "title": job.role,
            "company": job.company_name,
            "logo": job.company_logo or "fa-solid fa-briefcase",
            "internship_type": job.internship_type,
            "location_type": job.location_type,
            "stipend": job.stipend,
            "eligibility": job.eligibility,
            "skills": job.skills_required,
            "deadline": job.deadline,
            "official_link": job.official_link,
            "is_pinned": job.is_pinned,
            "compatibility": compatibility,
            "resume_match": resume_match,
            "recommended_certs": recommended_certs,
            "matched_skills": matched,
            "missing_skills": missing,
            "is_bookmarked": str(job.id) in bookmarked_ids
        })
        
    return render_template('internship_center.html', jobs=jobs, user_track=user_track, resume_score=resume_score)


# 8. Portfolio Builder
@features_bp.route('/portfolio-builder', methods=['GET'])
@login_required
def portfolio_builder():
    return render_template('portfolio_builder.html')

@features_bp.route('/portfolio-builder/generate', methods=['POST'])
@login_required
def portfolio_builder_generate():
    data = request.get_json() or {}
    theme = data.get('theme', 'modern')
    
    name = current_user.name or current_user.username.title()
    email = current_user.email
    branch = current_user.branch or "Computer Science"
    year = current_user.year or "3rd Year"
    track = current_user.career_goal or "Software Engineer"
    xp = current_user.xp
    
    # Try to extract projects and skills from the latest resume draft
    latest_resume = UserResume.query.filter_by(user_id=current_user.id).order_by(UserResume.updated_at.desc()).first()
    resume_content = {}
    if latest_resume:
        try:
            resume_content = json.loads(latest_resume.content_json)
        except Exception:
            pass
            
    # Extract projects
    projects_list = []
    proj_title = resume_content.get('projectTitle')
    if proj_title:
        desc_parts = []
        for bk in ['projectB1', 'projectB2', 'projectB3']:
            val = resume_content.get(bk)
            if val:
                desc_parts.append(val)
        proj_desc = " ".join(desc_parts) if desc_parts else "Built a project using modern web standards."
        projects_list.append({
            "title": proj_title,
            "desc": proj_desc,
            "tech": resume_content.get('skillsProg') or "Various Technologies"
        })
        
    if not projects_list:
        projects_list = [
            {"title": "CampusMate AI Core Engine", "desc": "Built a unified student platform mapping curriculum trees and ATS feedback workflows.", "tech": "Python, Flask, SQLite"},
            {"title": "Distributed Task Scheduler", "desc": "Implemented a concurrent cron scheduler containerized with Docker and monitored via Prometheus.", "tech": "Go, Docker, Prometheus"},
            {"title": "Real-time Chat Application", "desc": "Developed a full-stack real-time messaging workspace utilizing WebSockets and Redis memory cache.", "tech": "Node.js, Express, WebSockets, Redis"}
        ]
        
    # Extract skills
    skills_list = []
    for k in ['skillsProg', 'skillsWeb', 'skillsTools', 'skillsCyber']:
        val = resume_content.get(k)
        if val:
            skills_list.extend([s.strip() for s in val.split(',') if s.strip()])
    if not skills_list and current_user.skills:
        skills_list = [s.strip() for s in current_user.skills.split(',') if s.strip()]
    if not skills_list:
        skills_list = ["Python", "JavaScript", "HTML/CSS", "SQL"]
    skills = ", ".join(skills_list)
    
    if theme == "dark":
        bg = "#111827"
        text_primary = "#f3f4f6"
        text_secondary = "#9ca3af"
        accent = "#3b82f6"
        card_bg = "#1f2937"
        border = "#374151"
    elif theme == "gradient":
        bg = "#fafafa"
        text_primary = "#171717"
        text_secondary = "#737373"
        accent = "#ec4899"
        card_bg = "#ffffff"
        border = "#e5e5e5"
    else: # modern light
        bg = "#f8fafc"
        text_primary = "#0f172a"
        text_secondary = "#475569"
        accent = "#0f766e"
        card_bg = "#ffffff"
        border = "#e2e8f0"
        
    portfolio_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - Portfolio</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }}
        body {{ background-color: {bg}; color: {text_primary}; line-height: 1.6; padding: 2rem 1rem; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        header {{ margin-bottom: 3rem; text-align: center; }}
        header h1 {{ font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem; color: {accent}; }}
        header p {{ color: {text_secondary}; font-size: 1.1rem; }}
        .badge {{ display: inline-block; padding: 0.25rem 0.75rem; background: {accent}; color: white; border-radius: 50px; font-size: 0.8rem; margin: 0.25rem; font-weight: 600; }}
        section {{ margin-bottom: 3rem; }}
        h2 {{ font-size: 1.5rem; font-weight: 800; margin-bottom: 1rem; border-bottom: 2px solid {border}; padding-bottom: 0.5rem; }}
        .grid {{ display: grid; grid-template-columns: 1fr; gap: 1.5rem; }}
        @media (min-width: 600px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
        .card {{ background: {card_bg}; border: 1px solid {border}; padding: 1.5rem; border-radius: 8px; }}
        .card h3 {{ font-size: 1.15rem; margin-bottom: 0.5rem; }}
        .card p {{ color: {text_secondary}; font-size: 0.9rem; margin-bottom: 1rem; }}
        .contact {{ text-align: center; margin-top: 4rem; color: {text_secondary}; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{name}</h1>
            <p>{track} • {year} ({branch})</p>
            <p style="margin-top: 0.5rem; font-size: 0.95rem;">Learning Progress: <strong>{xp} XP</strong> accumulated in study track.</p>
        </header>
        
        <section>
            <h2>Skills & Technologies</h2>
            <div style="display: flex; flex-wrap: wrap; justify-content: center;">
                {" ".join(f'<span class="badge">{s.strip()}</span>' for s in skills.split(','))}
            </div>
        </section>
        
        <section>
            <h2>Featured Projects</h2>
            <div class="grid">
                {"".join(f'<div class="card"><h3>{p["title"]}</h3><p>{p["desc"]}</p><div style="font-size:0.8rem; font-weight:600; color:{accent};">{p["tech"]}</div></div>' for p in projects_list)}
            </div>
        </section>
        
        <section>
            <h2>Professional Profile</h2>
            <div class="card" style="width: 100%;">
                <p>Hello! I am a student pursuing career milestones in {branch}. I utilize automated AI advisors to structure my resume, practice interviews, and complete technical certifications.</p>
                <p style="margin-top: 0.5rem;">Feel free to contact me via email at: <strong>{email}</strong></p>
            </div>
        </section>
        
        <div class="contact">
            <p>Generated via CampusMate AI Portfolio Builder • 2026</p>
        </div>
    </div>
</body>
</html>"""
    return jsonify({"success": True, "html": portfolio_html})


# 9. Project Architect
@features_bp.route('/project-architect', methods=['GET'])
@login_required
def project_architect():
    return render_template('project_architect.html')

@features_bp.route('/project-architect/generate', methods=['POST'])
@login_required
def project_architect_generate():
    data = request.get_json() or {}
    idea = data.get('idea', '').strip()
    custom_key = data.get('custom_key', '').strip()
    
    if not idea:
        return jsonify({"success": False, "error": "Project idea is required"}), 400
        
    system_prompt = (
        "You are a Principal Software Architect. For the project idea provided, generate the project architecture blueprint. "
        "Provide your response in JSON format containing 4 keys:\n"
        "- \"folder_tree\": a text representation of the folder structure\n"
        "- \"config_file\": contents of a relevant Dockerfile or package.json\n"
        "- \"schema\": SQL table schemas or database models configuration\n"
        "- \"mermaid\": a mermaid diagram description (do not include markdown wrapper inside JSON values)"
    )
    user_prompt = f"Project Idea: {idea}"
    
    ai_res = call_gemini(system_prompt, user_prompt, user_key=custom_key)
    
    folder_tree = f"my-app/\n├── app/\n│   ├── __init__.py\n│   ├── models.py\n│   └── routes.py\n├── static/\n│   └── style.css\n├── templates/\n│   └── index.html\n├── Dockerfile\n├── requirements.txt\n└── database.db"
    config_file = "FROM python:3.12-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nEXPOSE 5000\nCMD [\"python\", \"main.py\"]"
    schema = "CREATE TABLE users (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    username TEXT UNIQUE NOT NULL,\n    email TEXT UNIQUE NOT NULL,\n    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);\n\nCREATE TABLE projects (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    user_id INTEGER FOREIGN KEY REFERENCES users(id),\n    title TEXT NOT NULL,\n    status TEXT DEFAULT 'draft'\n);"
    mermaid = "graph TD\n    Client[Web Client] -->|HTTP Request| Server[Flask API Server]\n    Server -->|SQL Queries| DB[(SQLite Database)]"
    
    if ai_res:
        try:
            json_match = re.search(r'\{.*\}', ai_res, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                folder_tree = parsed.get('folder_tree', folder_tree)
                config_file = parsed.get('config_file', config_file)
                schema = parsed.get('schema', schema)
                mermaid = parsed.get('mermaid', mermaid)
        except Exception:
            pass
            
    return jsonify({
        "success": True,
        "folder_tree": folder_tree,
        "config_file": config_file,
        "schema": schema,
        "mermaid": mermaid
    })


@features_bp.route('/internship-center/apply', methods=['POST'])
@login_required
def apply_internship():
    from app.models import AdminReview, Notification, UserResume
    
    job_id = request.form.get('job_id', type=int)
    if not job_id:
        return jsonify({"success": False, "error": "Job ID is required."}), 400
        
    # Check if they already applied
    existing = AdminReview.query.filter_by(user_id=current_user.id, job_id=job_id).first()
    if existing:
        return jsonify({"success": False, "error": "You have already requested a referral review for this position."}), 400
        
    # Get user's latest resume from UserResume table
    latest_resume = UserResume.query.filter_by(user_id=current_user.id).order_by(UserResume.updated_at.desc()).first()
    
    review = AdminReview(
        user_id=current_user.id,
        resume_id=latest_resume.id if latest_resume else None,
        job_id=job_id,
        status='pending'
    )
    db.session.add(review)
    db.session.commit()
    
    # Notify user
    notif = Notification(
        user_id=current_user.id,
        title="Referral Request Logged! 📩",
        content=f"Your referral request for Job #{job_id} has been submitted to the admin console.",
        category="general"
    )
    db.session.add(notif)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Your referral review request has been routed to the admin panel!"})





# --- RESUME 5.0 THEMES & EXPORT ENDPOINTS ---

THEME_STYLES = {
    # Original Themes (Classic)
    "classic": {"font": "Helvetica", "primary": "#1e293b", "bg": "#fffdfa"},
    "modern-cyan": {"font": "Helvetica", "primary": "#06b6d4", "bg": "#ffffff"},
    "slate-glass": {"font": "Helvetica", "primary": "#475569", "bg": "#ffffff"},
    "minimalist-executive": {"font": "Helvetica", "primary": "#1e293b", "bg": "#ffffff"},
    "tech-mono": {"font": "Courier", "primary": "#111827", "bg": "#ffffff"},
    "creative-violet": {"font": "Helvetica", "primary": "#7c3aed", "bg": "#ffffff"},
    "emerald-forest": {"font": "Helvetica", "primary": "#059669", "bg": "#ffffff"},
    "royal-indigo": {"font": "Helvetica", "primary": "#4f46e5", "bg": "#ffffff"},
    "corporate-navy": {"font": "Helvetica", "primary": "#1e3a8a", "bg": "#ffffff"},
    "modern-warm": {"font": "Helvetica", "primary": "#b45309", "bg": "#ffffff"},
    "clean-slate": {"font": "Helvetica", "primary": "#475569", "bg": "#ffffff"},
    "elegant-georgia": {"font": "Times-Roman", "primary": "#111827", "bg": "#ffffff"},
    "stanford-academic": {"font": "Times-Roman", "primary": "#8c1515", "bg": "#ffffff"},
    "sleek-tech": {"font": "Helvetica", "primary": "#1e293b", "bg": "#ffffff"},
    "compact-cv": {"font": "Helvetica", "primary": "#111827", "bg": "#ffffff"},
    "hybrid-columns": {"font": "Helvetica", "primary": "#1e293b", "bg": "#ffffff"},

    # 1. Student
    "student-academic": {"font": "Times-Roman", "primary": "#1e3a8a", "align": "center"},
    "student-entry": {"font": "Helvetica", "primary": "#0f766e", "bg": "#fafbfc"},
    "student-grad": {"font": "Times-Roman", "primary": "#1e293b"},
    "student-campus": {"font": "Helvetica", "primary": "#059669", "border_top": "6px solid #059669"},
    "student-scholar": {"font": "Times-Roman", "primary": "#111827"},
    
    # 2. ATS
    "ats-classic": {"font": "Times-Roman", "primary": "#111827", "align": "center"},
    "ats-modern": {"font": "Helvetica", "primary": "#111827"},
    "ats-minimal": {"font": "Helvetica", "primary": "#111827"},
    "ats-compact": {"font": "Helvetica", "primary": "#111827", "line_height": "1.1", "font_size": "8.5px"},
    "ats-formal": {"font": "Times-Roman", "primary": "#111827", "border": "1px double #374151"},
    
    # 3. Modern
    "modern-teal": {"font": "Helvetica", "primary": "#0d9488", "border_top": "6px solid #0d9488"},
    "modern-slate": {"font": "Helvetica", "primary": "#475569", "border_top": "6px solid #475569"},
    "modern-indigo": {"font": "Helvetica", "primary": "#4f46e5", "border_top": "6px solid #4f46e5"},
    "modern-coral": {"font": "Helvetica", "primary": "#f43f5e", "border_top": "6px solid #f43f5e"},
    "modern-glass": {"font": "Helvetica", "primary": "#0078d4", "border_top": "6px solid #0078d4"},
    
    # 4. Professional (MS)
    "ms-learn": {"font": "Helvetica", "primary": "#0078d4", "border_top": "6px solid #0078d4"},
    "ms-docs": {"font": "Helvetica", "primary": "#1e293b", "border_left": "6px solid #475569"},
    "ms-azure": {"font": "Helvetica", "primary": "#008ad7", "border_top": "6px solid #008ad7"},
    "ms-office": {"font": "Helvetica", "primary": "#004b87", "border_top": "3px solid #004b87"},
    "ms-team": {"font": "Helvetica", "primary": "#7f3d8a", "border_top": "6px solid #7f3d8a"},
    
    # 5. Internship
    "intern-general": {"font": "Helvetica", "primary": "#10b981", "border_top": "6px solid #10b981"},
    "intern-tech": {"font": "Courier", "primary": "#0f172a", "border_top": "6px solid #0f172a"},
    "intern-business": {"font": "Helvetica", "primary": "#1e3b8b", "border_top": "6px solid #1e3b8b"},
    "intern-creative": {"font": "Helvetica", "primary": "#ec4899", "border_top": "6px solid #ec4899"},
    "intern-research": {"font": "Helvetica", "primary": "#b45309", "border_top": "6px solid #b45309"},
    
    # 6. Cyber Security
    "cyber-mono": {"font": "Courier", "primary": "#16a34a", "color": "#16a34a"},
    "cyber-dark": {"font": "Helvetica", "primary": "#020617", "border_top": "6px solid #020617"},
    "cyber-shield": {"font": "Helvetica", "primary": "#1e3a8a", "border_top": "6px solid #1e3a8a"},
    "cyber-matrix": {"font": "Courier", "primary": "#22c55e", "border_top": "6px solid #22c55e"},
    "cyber-audit": {"font": "Helvetica", "primary": "#475569", "border_top": "6px solid #475569"},
    
    # 7. AI/ML
    "ai-tensor": {"font": "Helvetica", "primary": "#f97316", "border_top": "6px solid #f97316"},
    "ai-neural": {"font": "Helvetica", "primary": "#8b5cf6", "border_top": "6px solid #8b5cf6"},
    "ai-agent": {"font": "Helvetica", "primary": "#6366f1", "border_top": "6px solid #6366f1"},
    "ai-vision": {"font": "Helvetica", "primary": "#3b82f6", "border_top": "6px solid #3b82f6"},
    "ai-prompt": {"font": "Helvetica", "primary": "#14b8a6", "border_top": "6px solid #14b8a6"},
    
    # 8. Cloud
    "cloud-infra": {"font": "Helvetica", "primary": "#0284c7", "border_top": "6px solid #0284c7"},
    "cloud-ops": {"font": "Helvetica", "primary": "#10b981", "border_top": "6px solid #0f172a"},
    "cloud-k8s": {"font": "Helvetica", "primary": "#38bdf8", "border_left": "6px solid #38bdf8"},
    "cloud-aws": {"font": "Helvetica", "primary": "#ff9900", "border_top": "4px solid #111"},
    "cloud-hybrid": {"font": "Helvetica", "primary": "#6b21a8", "border_left": "6px solid #6b21a8"},
    
    # 9. Software Engineering
    "swe-git": {"font": "Helvetica", "primary": "#24292f", "border_top": "6px solid #24292f"},
    "swe-fullstack": {"font": "Helvetica", "primary": "#6366f1", "border_top": "6px solid #6366f1"},
    "swe-backend": {"font": "Helvetica", "primary": "#0f172a", "border_top": "6px solid #0f172a"},
    "swe-frontend": {"font": "Helvetica", "primary": "#06b6d4", "border_top": "6px solid #06b6d4"},
    "swe-cloud": {"font": "Helvetica", "primary": "#0ea5e9", "border_top": "6px solid #0ea5e9"},
    
    # 10. Minimal
    "minimal-light": {"font": "Helvetica", "primary": "#1f2937"},
    "minimal-dark": {"font": "Helvetica", "primary": "#0f172a", "bg": "#fafbfc"},
    "minimal-border": {"font": "Helvetica", "primary": "#cbd5e1", "border": "1px solid #cbd5e1"},
    "minimal-compact": {"font": "Helvetica", "primary": "#1f2937", "line_height": "1.1", "font_size": "8.5px"},
    "minimal-swiss": {"font": "Helvetica", "primary": "#000"},
    
    # 11. Executive
    "exec-director": {"font": "Times-Roman", "primary": "#b45309", "border_top": "6px solid #b45309"},
    "exec-vp": {"font": "Helvetica", "primary": "#1e293b", "border_top": "6px solid #1e293b"},
    "exec-board": {"font": "Times-Roman", "primary": "#000", "align": "center"},
    "exec-legal": {"font": "Times-Roman", "primary": "#000"},
    "exec-partner": {"font": "Times-Roman", "primary": "#1e3a8a", "border_top": "6px solid #1e3a8a"},
    
    # 12. Canva-style Premium Themes
    "canva-sidebar": {"font": "Helvetica", "primary": "#0d9488", "bg": "#ffffff"},
    "canva-elegant": {"font": "Helvetica", "primary": "#1e3b8b", "bg": "#ffffff"},
    "canva-split": {"font": "Helvetica", "primary": "#1f2937", "bg": "#ffffff"}
}

def render_resume_pdf_html(content, theme):
    style_config = THEME_STYLES.get(theme, THEME_STYLES["classic"])
    font = style_config.get("font", "Helvetica")
    primary = style_config.get("primary", "#111827")
    bg = style_config.get("bg", "#ffffff")
    text_color = style_config.get("color", "#374151")
    align = style_config.get("align", "left")
    border_top = style_config.get("border_top", "none")
    border_left = style_config.get("border_left", "none")
    border_bottom = style_config.get("border_bottom", "none")
    border = style_config.get("border", "none")
    line_h = style_config.get("line_height", "1.3")
    f_size = style_config.get("font_size", "9.5px")
    
    # 1. Parse Education List
    edu_list = content.get('education')
    if edu_list and isinstance(edu_list, list):
        edu_entries = edu_list
    else:
        edu_entries = []
        inst1 = content.get('edu1Inst', '').strip()
        deg1 = content.get('edu1Degree', '').strip()
        if inst1 or deg1:
            edu_entries.append({
                "inst": inst1,
                "degree": deg1,
                "dates": content.get('edu1Dates', '').strip(),
                "gpa": content.get('edu1Gpa', '').strip(),
                "coursework": content.get('edu1Coursework', '').strip()
            })
        inst2 = content.get('edu2Inst', '').strip()
        deg2 = content.get('edu2Degree', '').strip()
        if inst2 or deg2:
            edu_entries.append({
                "inst": inst2,
                "degree": deg2,
                "dates": content.get('edu2Dates', '').strip(),
                "gpa": content.get('edu2Gpa', '').strip(),
                "coursework": ""
            })

    # 2. Parse Experience List
    exp_list = content.get('experience')
    if exp_list and isinstance(exp_list, list):
        exp_entries = exp_list
    else:
        exp_entries = []
        role = content.get('experienceRole', '').strip()
        comp = content.get('experienceComp', '').strip()
        if role or comp:
            bullets = []
            b1 = content.get('experienceB1', '').strip()
            b2 = content.get('experienceB2', '').strip()
            b3 = content.get('experienceB3', '').strip()
            b4 = content.get('experienceB4', '').strip()
            if b1: bullets.append(b1)
            if b2: bullets.append(b2)
            if b3: bullets.append(b3)
            if b4: bullets.append(b4)
            exp_entries.append({
                "role": role,
                "company": comp,
                "dates": content.get('experienceDates', '').strip(),
                "bullets": bullets
            })

    # 3. Parse Projects List
    proj_list = content.get('projects')
    if proj_list and isinstance(proj_list, list):
        proj_entries = proj_list
    else:
        proj_entries = []
        title = content.get('projectTitle', '').strip()
        if title:
            bullets = []
            pb1 = content.get('projectB1', '').strip()
            pb2 = content.get('projectB2', '').strip()
            pb3 = content.get('projectB3', '').strip()
            if pb1: bullets.append(pb1)
            if pb2: bullets.append(pb2)
            if pb3: bullets.append(pb3)
            proj_entries.append({
                "title": title,
                "link": content.get('projectLink', '').strip(),
                "bullets": bullets
            })

    # 4. Parse Certifications List
    cert_list = content.get('certifications')
    if cert_list and isinstance(cert_list, list):
        cert_entries = cert_list
    else:
        cert_entries = []
        c1 = content.get('certC1', '').strip()
        c2 = content.get('certC2', '').strip()
        c3 = content.get('certC3', '').strip()
        c4 = content.get('certC4', '').strip()
        if c1: cert_entries.append({"name": c1})
        if c2: cert_entries.append({"name": c2})
        if c3: cert_entries.append({"name": c3})
        if c4: cert_entries.append({"name": c4})

    order = content.get('sectionOrder', ["education", "schoolcollege", "skills", "experience", "projects", "certifications", "customSection", "achievements", "hackathons", "languages"])
    
    school_list = content.get('schoolCollege', [])
    if not isinstance(school_list, list):
        school_list = []
        
    cust_sec = content.get('customSection', {})
    if not isinstance(cust_sec, dict):
        cust_sec = {}
    cust_sec_title = cust_sec.get('title', '').strip()
    cust_sec_bullets = cust_sec.get('bullets', [])
    if not isinstance(cust_sec_bullets, list):
        cust_sec_bullets = []
        
    addr = content.get('address', '').strip()
    email = content.get('email', '').strip()
    phone = content.get('phone', '').strip()
    linkedin = content.get('linkedin', '').strip()
    github = content.get('github', '').strip()
    portfolio = content.get('portfolio', '').strip()
    leetcode = content.get('leetcode', '').strip()
    hackerrank = content.get('hackerrank', '').strip()
    codeforces = content.get('codeforces', '').strip()
    headline = content.get('headline', '').strip()
    
    meta_parts = []
    if addr: meta_parts.append(addr)
    if email: meta_parts.append(f'<a href="mailto:{email}" style="color: {primary}; text-decoration: none;">{email}</a>')
    if phone: meta_parts.append(f'<a href="tel:{phone}" style="color: {primary}; text-decoration: none;">{phone}</a>')
    if linkedin:
        linkedin_url = linkedin if linkedin.startswith('http') else f"https://{linkedin}"
        meta_parts.append(f'<a href="{linkedin_url}" style="color: {primary}; text-decoration: none;">{linkedin}</a>')
    if github:
        github_url = github if github.startswith('http') else f"https://{github}"
        meta_parts.append(f'<a href="{github_url}" style="color: {primary}; text-decoration: none;">{github}</a>')
    if portfolio:
        portfolio_url = portfolio if portfolio.startswith('http') else f"https://{portfolio}"
        meta_parts.append(f'<a href="{portfolio_url}" style="color: {primary}; text-decoration: none;">{portfolio}</a>')
    if leetcode:
        leetcode_url = leetcode if leetcode.startswith('http') else f"https://{leetcode}"
        meta_parts.append(f'<a href="{leetcode_url}" style="color: {primary}; text-decoration: none;">LeetCode: {leetcode}</a>')
    if hackerrank:
        hackerrank_url = hackerrank if hackerrank.startswith('http') else f"https://{hackerrank}"
        meta_parts.append(f'<a href="{hackerrank_url}" style="color: {primary}; text-decoration: none;">HackerRank: {hackerrank}</a>')
    if codeforces:
        codeforces_url = codeforces if codeforces.startswith('http') else f"https://{codeforces}"
        meta_parts.append(f'<a href="{codeforces_url}" style="color: {primary}; text-decoration: none;">Codeforces: {codeforces}</a>')

    # TWO-COLUMN CANVA TEMPLATES (canva-sidebar and canva-split)
    if theme in ["canva-sidebar", "canva-split"]:
        is_dark = (theme == "canva-sidebar")
        left_bg = "#0d9488" if is_dark else "#ffffff"
        left_color = "#ffffff" if is_dark else "#374151"
        left_border = "none" if is_dark else "border-right: 1px solid #cbd5e1;"
        divider_color = "#ffffff" if is_dark else "#cbd5e1"
        accent_color = "#ffffff" if is_dark else primary
        
        # Left sidebar html
        left_html = ""
        pic_url = content.get('profilePic', '').strip()
        if not pic_url and current_user.is_authenticated and current_user.profile_photo:
            import os
            pic_url = os.path.join(current_app.root_path, 'static', current_user.profile_photo).replace('\\', '/')
        if pic_url:
            left_html += f'<div style="text-align: center; margin-bottom: 12px;"><img src="{pic_url}" style="width: 70px; height: 70px; border-radius: 35px; border: 2px solid {"#ffffff" if is_dark else primary};" /></div>'
            
        left_html += '<div style="margin-bottom: 12px;">'
        left_html += f'<h4 style="font-size: 9.5px; font-weight: bold; border-bottom: 0.75px solid {divider_color}; padding-bottom: 1.5px; margin-bottom: 5px; text-transform: uppercase; color: {accent_color};">Contact</h4>'
        left_html += f'<div style="font-size: 8.5px; line-height: 1.35; color: {"#e2e8f0" if is_dark else "#4b5563"};">'
        if addr: left_html += f'<div style="margin-bottom: 3.5px;">📍 {addr}</div>'
        if email: left_html += f'<div style="margin-bottom: 3.5px;">✉️ <a href="mailto:{email}" style="color: inherit; text-decoration: none;">{email}</a></div>'
        if phone: left_html += f'<div style="margin-bottom: 3.5px;">📞 <a href="tel:{phone}" style="color: inherit; text-decoration: none;">{phone}</a></div>'
        if linkedin:
            linkedin_url = linkedin if linkedin.startswith('http') else f"https://{linkedin}"
            left_html += f'<div style="margin-bottom: 3.5px;">🔗 <a href="{linkedin_url}" style="color: inherit; text-decoration: none;">{linkedin}</a></div>'
        if github:
            github_url = github if github.startswith('http') else f"https://{github}"
            left_html += f'<div style="margin-bottom: 3.5px;">🐙 <a href="{github_url}" style="color: inherit; text-decoration: none;">{github}</a></div>'
        if portfolio:
            portfolio_url = portfolio if portfolio.startswith('http') else f"https://{portfolio}"
            left_html += f'<div style="margin-bottom: 3.5px;">🌐 <a href="{portfolio_url}" style="color: inherit; text-decoration: none;">{portfolio}</a></div>'
        if leetcode:
            leetcode_url = leetcode if leetcode.startswith('http') else f"https://{leetcode}"
            left_html += f'<div style="margin-bottom: 3.5px;">💻 <a href="{leetcode_url}" style="color: inherit; text-decoration: none;">LC: {leetcode}</a></div>'
        if hackerrank:
            hackerrank_url = hackerrank if hackerrank.startswith('http') else f"https://{hackerrank}"
            left_html += f'<div style="margin-bottom: 3.5px;">💻 <a href="{hackerrank_url}" style="color: inherit; text-decoration: none;">HR: {hackerrank}</a></div>'
        if codeforces:
            codeforces_url = codeforces if codeforces.startswith('http') else f"https://{codeforces}"
            left_html += f'<div style="margin-bottom: 3.5px;">💻 <a href="{codeforces_url}" style="color: inherit; text-decoration: none;">CF: {codeforces}</a></div>'
        left_html += '</div></div>'
        
        # Skills
        skills_prog = content.get('skillsProg', '').strip()
        skills_cyber = content.get('skillsCyber', '').strip()
        skills_tools = content.get('skillsTools', '').strip()
        skills_web = content.get('skillsWeb', '').strip()
        if skills_prog or skills_cyber or skills_tools or skills_web:
            left_html += '<div style="margin-bottom: 12px;">'
            left_html += f'<h4 style="font-size: 9.5px; font-weight: bold; border-bottom: 0.75px solid {divider_color}; padding-bottom: 1.5px; margin-bottom: 5px; text-transform: uppercase; color: {accent_color};">Skills</h4>'
            left_html += f'<div style="font-size: 8.5px; line-height: 1.35; color: {"#e2e8f0" if is_dark else "#4b5563"};">'
            if skills_prog: left_html += f'<div style="margin-bottom: 3.5px;"><strong>Lang:</strong> {skills_prog}</div>'
            if skills_cyber: left_html += f'<div style="margin-bottom: 3.5px;"><strong>Cyber:</strong> {skills_cyber}</div>'
            if skills_tools: left_html += f'<div style="margin-bottom: 3.5px;"><strong>Tools:</strong> {skills_tools}</div>'
            if skills_web: left_html += f'<div style="margin-bottom: 3.5px;"><strong>Web:</strong> {skills_web}</div>'
            left_html += '</div></div>'
            
        # Languages & Interests
        langs = content.get('languages', '').strip()
        interests = content.get('interests', '').strip()
        if langs or interests:
            left_html += '<div style="margin-bottom: 12px;">'
            left_html += f'<h4 style="font-size: 8px; font-weight: bold; border-bottom: 0.75px solid {divider_color}; padding-bottom: 1px; margin-bottom: 4px; text-transform: uppercase; color: {accent_color};">Languages</h4>'
            left_html += f'<div style="font-size: 7px; line-height: 1.3; color: {"#e2e8f0" if is_dark else "#4b5563"};">'
            if langs: left_html += f'<div style="margin-bottom: 2px;"><strong>Langs:</strong> {langs}</div>'
            if interests: left_html += f'<div style="margin-bottom: 2px;"><strong>Interests:</strong> {interests}</div>'
            left_html += '</div></div>'
            
        # Right Panel
        right_html = ""
        name_val = content.get('name', 'Alex Smith')
        summary_val = content.get('custom', '').strip()
        
        right_html += f'<h1 style="font-size: 18px; font-weight: bold; color: {primary}; margin-bottom: 2px; text-transform: uppercase;">{name_val}</h1>'
        right_html += f'<div style="font-size: 8px; font-weight: bold; color: #64748b; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px;">{headline if headline else "Resume Portfolio"}</div>'
        
        if summary_val:
            right_html += f'<div style="font-size: 8px; line-height: 1.3; color: #4b5563; margin-bottom: 10px; border-left: 2px solid {primary}; padding-left: 6px;">{summary_val}</div>'
            
        for sec in order:
            if sec == "experience" and exp_entries:
                right_html += f'<div style="margin-bottom: 10px;"><h4 style="font-size: 9px; font-weight: bold; color: {primary}; border-bottom: 0.75px solid #cbd5e1; padding-bottom: 1px; margin-bottom: 4px; text-transform: uppercase;">Experience</h4>'
                for exp in exp_entries:
                    role = exp.get('role', '').strip()
                    comp = exp.get('company', '').strip()
                    dates = exp.get('dates', '').strip()
                    bullets = exp.get('bullets', [])
                    if role or comp:
                        right_html += f"""
                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 3px;">
                            <tr>
                                <td style="font-size: 8px; font-weight: bold; color: #1e293b;">{role}</td>
                                <td style="font-size: 7.5px; text-align: right; color: #64748b;">{dates}</td>
                            </tr>
                            <tr>
                                <td colspan="2" style="font-size: 7.5px; font-style: italic; color: #475569;">{comp}</td>
                            </tr>
                        </table>
                        """
                        if bullets:
                            right_html += '<ul style="margin: 0 0 4px 0; padding-left: 10px; font-size: 7.5px; line-height: 1.25; color: #4b5563;">'
                            for b in bullets:
                                if b.strip():
                                    right_html += f'<li style="margin-bottom: 1px;">{b.strip()}</li>'
                            right_html += '</ul>'
                right_html += '</div>'
                
            elif sec == "projects" and proj_entries:
                right_html += f'<div style="margin-bottom: 10px;"><h4 style="font-size: 9px; font-weight: bold; color: {primary}; border-bottom: 0.75px solid #cbd5e1; padding-bottom: 1px; margin-bottom: 4px; text-transform: uppercase;">Projects</h4>'
                for proj in proj_entries:
                    title = proj.get('title', '').strip()
                    link = proj.get('link', '').strip()
                    bullets = proj.get('bullets', [])
                    if title:
                        right_html += f"""
                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 3px;">
                            <tr>
                                <td style="font-size: 8px; font-weight: bold; color: #1e293b;">{title}</td>
                                <td style="font-size: 7.5px; text-align: right; color: #64748b;">{link}</td>
                            </tr>
                        </table>
                        """
                        if bullets:
                            right_html += '<ul style="margin: 0 0 4px 0; padding-left: 10px; font-size: 7.5px; line-height: 1.25; color: #4b5563;">'
                            for b in bullets:
                                if b.strip():
                                    right_html += f'<li style="margin-bottom: 1px;">{b.strip()}</li>'
                            right_html += '</ul>'
                right_html += '</div>'
                
            elif sec == "education" and edu_entries:
                right_html += f'<div style="margin-bottom: 10px;"><h4 style="font-size: 9px; font-weight: bold; color: {primary}; border-bottom: 0.75px solid #cbd5e1; padding-bottom: 1px; margin-bottom: 4px; text-transform: uppercase;">Education</h4>'
                for edu in edu_entries:
                    inst = edu.get('inst', '').strip()
                    degree = edu.get('degree', '').strip()
                    dates = edu.get('dates', '').strip()
                    gpa = edu.get('gpa', '').strip()
                    cw = edu.get('coursework', '').strip()
                    if inst or degree:
                        right_html += f"""
                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 2px;">
                            <tr>
                                <td style="font-size: 8px; font-weight: bold; color: #1e293b;">{inst}</td>
                                <td style="font-size: 7.5px; text-align: right; color: #64748b;">{dates}</td>
                            </tr>
                            <tr>
                                <td style="font-size: 7.5px; font-style: italic; color: #475569;">{degree}</td>
                                <td style="font-size: 7.5px; text-align: right; color: #475569;">{gpa}</td>
                            </tr>
                        </table>
                        """
                        if cw:
                            right_html += f'<div style="font-size: 7px; color: #64748b; margin-top: 1px; margin-bottom: 2px;">Relevant Coursework: {cw}</div>'
                right_html += '</div>'
                
            elif sec == "schoolcollege" and school_list:
                right_html += f'<div style="margin-bottom: 10px;"><h4 style="font-size: 9px; font-weight: bold; color: {primary}; border-bottom: 0.75px solid #cbd5e1; padding-bottom: 1px; margin-bottom: 4px; text-transform: uppercase;">School & College List</h4>'
                right_html += '<ul style="margin: 0; padding-left: 10px; font-size: 7.5px; line-height: 1.25; color: #4b5563;">'
                for item in school_list:
                    name = item.get('name', '').strip()
                    if name:
                        right_html += f'<li style="margin-bottom: 1px;">{name}</li>'
                right_html += '</ul></div>'

            elif sec == "certifications" and cert_entries:
                right_html += f'<div style="margin-bottom: 10px;"><h4 style="font-size: 9px; font-weight: bold; color: {primary}; border-bottom: 0.75px solid #cbd5e1; padding-bottom: 1px; margin-bottom: 4px; text-transform: uppercase;">Certifications</h4>'
                right_html += '<ul style="margin: 0; padding-left: 10px; font-size: 7.5px; line-height: 1.25; color: #4b5563;">'
                for cert in cert_entries:
                    name = cert.get('name', '').strip()
                    if name:
                        right_html += f'<li style="margin-bottom: 1px;">{name}</li>'
                right_html += '</ul></div>'
                
            elif sec == "customSection" and cust_sec_title:
                right_html += f'<div style="margin-bottom: 10px;"><h4 style="font-size: 9px; font-weight: bold; color: {primary}; border-bottom: 0.75px solid #cbd5e1; padding-bottom: 1px; margin-bottom: 4px; text-transform: uppercase;">{cust_sec_title}</h4>'
                if cust_sec_bullets:
                    right_html += '<ul style="margin: 0; padding-left: 10px; font-size: 7.5px; line-height: 1.25; color: #4b5563;">'
                    for b in cust_sec_bullets:
                        if b.strip():
                            right_html += f'<li style="margin-bottom: 1px;">{b.strip()}</li>'
                    right_html += '</ul>'
                right_html += '</div>'

            elif sec == "achievements" and content.get('achievements', '').strip():
                ach = content.get('achievements', '').strip()
                right_html += f'<div style="margin-bottom: 10px;"><h4 style="font-size: 9px; font-weight: bold; color: {primary}; border-bottom: 0.75px solid #cbd5e1; padding-bottom: 1px; margin-bottom: 4px; text-transform: uppercase;">Achievements</h4><div style="font-size: 7.5px; line-height: 1.25; color: #4b5563;">{ach}</div></div>'
                
        # output pdf wrapper with tables
        full_html = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{
                    size: a4;
                    margin: 0mm;
                }}
                body {{
                    font-family: {font};
                    font-size: 8px;
                    background-color: #ffffff;
                    color: #374151;
                    margin: 0mm;
                    padding: 0mm;
                }}
            </style>
        </head>
        <body>
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="height: 285mm; table-layout: fixed;">
                <tr>
                    <td width="30%" bgcolor="{left_bg}" valign="top" style="padding: 8mm 5mm 8mm 5mm; color: {left_color}; {left_border}">
                        {left_html}
                    </td>
                    <td width="70%" bgcolor="#ffffff" valign="top" style="padding: 8mm 8mm 8mm 8mm; color: #374151;">
                        {right_html}
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        return full_html

    # SINGLE-COLUMN RENDERING (Standard and canva-elegant)
    is_elegant = (theme == "canva-elegant")
    
    container_styles = []
    if border_top != "none":
        container_styles.append(f"border-top: {border_top}; padding-top: 8px;")
    if border_left != "none":
        container_styles.append(f"border-left: {border_left}; padding-left: 12px;")
    if border_bottom != "none":
        container_styles.append(f"border-bottom: {border_bottom};")
    if border != "none":
        container_styles.append(f"border: {border}; padding: 12px;")
        
    container_css_str = "\n        ".join(container_styles)
    
    css = f"""
    @page {{
        size: a4;
        margin-top: 10mm;
        margin-bottom: 10mm;
        margin-left: 12mm;
        margin-right: 12mm;
    }}
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}
    body {{
        font-family: {font}, 'Helvetica Neue', Arial, sans-serif;
        font-size: {f_size};
        line-height: {line_h};
        color: {text_color};
        background-color: {bg};
    }}
    .resume-container {{
        {container_css_str}
    }}
    table, tr, td, th {{
        border: none !important;
        border-collapse: collapse;
    }}
    ul, li, p, span, h1, h2, h3, h4, h5, h6 {{
        border: none !important;
    }}
    a {{
        color: {primary};
        text-decoration: none;
    }}
    h1 {{
        font-size: 20px;
        font-weight: 700;
        color: {primary};
        margin: 0 0 2px 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .meta {{
        font-size: 8.5px;
        color: #4b5563;
        line-height: 1.4;
        margin-top: 2px;
        margin-bottom: 6px;
    }}
    .meta a {{
        color: {primary};
        text-decoration: none;
    }}
    .resume-section {{
        page-break-inside: avoid;
        margin-bottom: 2px;
    }}
    .section-title {{
        font-size: 10.5px;
        font-weight: 700;
        color: {primary};
        border-bottom: 1px solid {primary};
        margin-top: 8px;
        margin-bottom: 4px;
        padding-bottom: 1.5px;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}
    .item-header {{
        font-size: 9.5px;
        font-weight: 700;
        color: #1e293b;
    }}
    .item-date {{
        font-size: 9px;
        text-align: right;
        color: #4b5563;
    }}
    .bullet-list {{
        margin-top: 1px;
        margin-bottom: 3px;
        padding-left: 14px;
        list-style-type: disc;
    }}
    .bullet-item {{
        margin-bottom: 1px;
        font-size: 9px;
        line-height: 1.35;
        color: #374151;
    }}
    hr {{
        border: none;
        border-top: 0.5px solid #d1d5db;
        margin: 4px 0;
    }}
    """

    
    # Render sections
    sections_html = ""
    
    summary_val = content.get('custom', '').strip()
    if summary_val:
        sections_html += f'<div style="font-size: 9px; line-height: 1.35; color: #4b5563; margin-bottom: 8px; text-align: {"center" if is_elegant else "left"};">{summary_val}</div>'

    for sec in order:
        if sec == "education" and edu_entries:
            sections_html += f"""
            <div class="resume-section">
                <h3 class="section-title" style="text-align: {"center" if is_elegant else "left"};">Education</h3>
            """
            for edu in edu_entries:
                inst = edu.get('inst', '').strip()
                degree = edu.get('degree', '').strip()
                dates = edu.get('dates', '').strip()
                gpa = edu.get('gpa', '').strip()
                cw = edu.get('coursework', '').strip()
                if inst or degree:
                    sections_html += f"""
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 3px;">
                        <tr>
                            <td class="item-header">{inst}</td>
                            <td class="item-date">{dates}</td>
                        </tr>
                        <tr>
                            <td style="font-style: italic; font-size: 9px; color: #4b5563;">{degree}</td>
                            <td style="text-align: right; font-size: 9px; color: #4b5563;">{gpa}</td>
                        </tr>
                    </table>
                    """
                    if cw:
                        sections_html += f'<div style="margin-top: 2px; margin-bottom: 4px; font-size: 9px; color: #4b5563;">Relevant Coursework: {cw}</div>'
            sections_html += "</div>"
            
        elif sec == "skills":
            prog = content.get('skillsProg', '').strip()
            cyber = content.get('skillsCyber', '').strip()
            tools = content.get('skillsTools', '').strip()
            web = content.get('skillsWeb', '').strip()
            
            if prog or cyber or tools or web:
                sections_html += f"""
                <div class="resume-section">
                    <h3 class="section-title" style="text-align: {"center" if is_elegant else "left"};">Technical Skills</h3>
                    <table width="100%" cellpadding="2" cellspacing="0" style="font-size: 9px; line-height: 1.35;">
                """
                if prog:
                    sections_html += f'<tr><td width="22%"><strong>Programming:</strong></td><td>{prog}</td></tr>'
                if cyber:
                    sections_html += f'<tr><td width="22%"><strong>Cybersecurity & DB:</strong></td><td>{cyber}</td></tr>'
                if tools:
                    sections_html += f'<tr><td width="22%"><strong>Tools & OS:</strong></td><td>{tools}</td></tr>'
                if web:
                    sections_html += f'<tr><td width="22%"><strong>Web & Libraries:</strong></td><td>{web}</td></tr>'
                sections_html += """
                    </table>
                </div>
                """
                
        elif sec == "experience" and exp_entries:
            sections_html += f"""
            <div class="resume-section">
                <h3 class="section-title" style="text-align: {"center" if is_elegant else "left"};">Experience</h3>
            """
            for exp in exp_entries:
                role = exp.get('role', '').strip()
                comp = exp.get('company', '').strip()
                dates = exp.get('dates', '').strip()
                bullets = exp.get('bullets', [])
                if role or comp:
                    sections_html += f"""
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 2px; margin-bottom: 2px;">
                        <tr>
                            <td class="item-header">{role}</td>
                            <td class="item-date">{dates}</td>
                        </tr>
                        <tr>
                            <td colspan="2" style="font-style: italic; font-size: 9px; color: #4b5563; padding-top: 1px;">{comp}</td>
                        </tr>
                    </table>
                    """
                    if bullets:
                        sections_html += '<ul class="bullet-list">'
                        for b in bullets:
                            if b.strip():
                                sections_html += f'<li class="bullet-item">{b.strip()}</li>'
                        sections_html += '</ul>'
            sections_html += "</div>"
            
        elif sec == "projects" and proj_entries:
            sections_html += f"""
            <div class="resume-section">
                <h3 class="section-title" style="text-align: {"center" if is_elegant else "left"};">Projects</h3>
            """
            for proj in proj_entries:
                title = proj.get('title', '').strip()
                link = proj.get('link', '').strip()
                bullets = proj.get('bullets', [])
                if title:
                    proj_link_html = link
                    if link:
                        proj_link_url = link if link.startswith('http') else f"https://{link}"
                        proj_link_html = f'<a href="{proj_link_url}" style="color: {primary}; text-decoration: underline;">{link}</a>'
                    sections_html += f"""
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin-top: 2px; margin-bottom: 2px;">
                        <tr>
                            <td class="item-header">{title}</td>
                            <td class="item-date" style="font-weight: normal; font-size: 9px;">{proj_link_html}</td>
                        </tr>
                    </table>
                    """
                    if bullets:
                        sections_html += '<ul class="bullet-list">'
                        for b in bullets:
                            if b.strip():
                                sections_html += f'<li class="bullet-item">{b.strip()}</li>'
                        sections_html += '</ul>'
            sections_html += "</div>"
            
        elif sec == "certifications" and cert_entries:
            sections_html += f"""
            <div class="resume-section">
                <h3 class="section-title" style="text-align: {"center" if is_elegant else "left"};">Certifications</h3>
                <ul class="bullet-list">
            """
            for cert in cert_entries:
                name = cert.get('name', '').strip()
                if name:
                    sections_html += f'<li class="bullet-item">{name}</li>'
            sections_html += """
                </ul>
            </div>
            """
            
        elif sec == "achievements" and content.get('achievements', '').strip():
            ach = content.get('achievements', '').strip()
            sections_html += f"""
            <div class="resume-section">
                <h3 class="section-title" style="text-align: {"center" if is_elegant else "left"};">Achievements</h3>
                <div style="font-size: 9px; line-height: 1.35; color: #374151;">{ach}</div>
            </div>
            """
            
        elif sec == "hackathons":
            hacks = content.get('hackathons', '').strip()
            workshops = content.get('workshops', '').strip()
            if hacks or workshops:
                sections_html += f"""
                <div class="resume-section">
                    <h3 class="section-title" style="text-align: {"center" if is_elegant else "left"};">Hackathons & Workshops</h3>
                """
                if hacks:
                    sections_html += f'<div style="font-size: 9px; line-height: 1.35; margin-bottom: 3px;"><strong>Hackathons:</strong> {hacks}</div>'
                if workshops:
                    sections_html += f'<div style="font-size: 9px; line-height: 1.35;"><strong>Workshops:</strong> {workshops}</div>'
                sections_html += "</div>"
                
        elif sec == "languages":
            langs = content.get('languages', '').strip()
            interests = content.get('interests', '').strip()
            if langs or interests:
                sections_html += f"""
                <div class="resume-section">
                    <h3 class="section-title" style="text-align: {"center" if is_elegant else "left"};">Languages & Interests</h3>
                """
                if langs:
                    sections_html += f'<div style="font-size: 9px; line-height: 1.35; margin-bottom: 3px;"><strong>Languages:</strong> {langs}</div>'
                if interests:
                    sections_html += f'<div style="font-size: 9px; line-height: 1.35;"><strong>Interests:</strong> {interests}</div>'
                sections_html += "</div>"

    meta_str = (" &bull; " if is_elegant else " | ").join(meta_parts)
    
    full_html = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            {css}
        </style>
    </head>
    <body>
        <div class="resume-container">
            <div style="text-align: {"center" if is_elegant else align}; margin-bottom: 8px;">
                <h1>{content.get('name', 'Alex Smith')}</h1>
                <div class="meta">{meta_str}</div>
            </div>
            {sections_html}
        </div>
    </body>
    </html>
    """
    return full_html


@features_bp.route('/resume-analyzer/export-pdf', methods=['POST'])
@login_required
def export_pdf():
    try:
        data = request.get_json() or {}
        content = data.get('content', {})
        theme = data.get('theme', 'classic')
        preview_html = data.get('preview_html')
        
        if preview_html:
            import os
            # Read styles from style.css
            css_path = os.path.join(current_app.root_path, 'static', 'css', 'style.css')
            css_content = ""
            if os.path.exists(css_path):
                with open(css_path, 'r', encoding='utf-8') as f:
                    css_content = f.read()
                    
            # WeasyPrint layout and pagination styles
            pdf_styles = """
            @page {
                size: a4;
                margin: 0;
            }
            body {
                margin: 0;
                padding: 0;
                background: #ffffff !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            .resume-sheet {
                width: 210mm !important;
                min-height: 297mm !important;
                box-shadow: none !important;
                border: none !important;
                border-radius: 0 !important;
                margin: 0 auto !important;
                padding: 15mm !important;
                box-sizing: border-box !important;
                position: relative !important;
                transform: none !important;
                overflow: visible !important;
                background: #ffffff !important;
                color: #000000 !important;
            }
            /* Avoid page breaks inside sections */
            .resume-section, .resume-render-section, [data-section] {
                page-break-inside: avoid !important;
                break-inside: avoid !important;
            }
            """
            
            html_content = f"""<!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.5.2/css/all.min.css">
                <style>
                    {css_content}
                    {pdf_styles}
                </style>
            </head>
            <body>
                <div class="resume-sheet {theme}">
                    {preview_html}
                </div>
            </body>
            </html>
            """
        else:
            html_content = render_resume_pdf_html(content, theme)
        
        if weasyprint is not None:
            # Generate PDF using WeasyPrint
            pdf_bytes = weasyprint.HTML(string=html_content, base_url=request.base_url).write_pdf()
            name_val = content.get('name', 'Resume').strip().replace(' ', '_')
            filename = f"{name_val}_Resume.pdf"
            
            response = make_response(pdf_bytes)
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            response.headers['Content-Type'] = 'application/pdf'
            return response
        else:
            # WeasyPrint is not available (such as in local windows dev without GTK installed)
            # Return error so the client-side html2pdf.js fallback is triggered instantly
            return jsonify({
                "success": False, 
                "error": "WeasyPrint is not available on this server. Falling back to browser-side PDF engine."
            }), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@features_bp.route('/resume-analyzer/export-json', methods=['POST'])
@login_required
def export_json():
    try:
        data = request.get_json() or {}
        content = data.get('content', {})
        
        name_val = content.get('name', 'Resume').strip().replace(' ', '_')
        filename = f"{name_val}_Resume.json"
        
        buffer = BytesIO(json.dumps(content, indent=2).encode('utf-8'))
        response = make_response(buffer.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@features_bp.route('/resume-analyzer/duplicate-version', methods=['POST'])
@login_required
def duplicate_version():
    try:
        data = request.get_json() or {}
        resume_id = data.get('id')
        new_title = data.get('title', 'Copy of Resume')
        
        if not resume_id:
            return jsonify({"success": False, "error": "Resume ID required"}), 400
            
        orig = UserResume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not orig:
            return jsonify({"success": False, "error": "Resume not found"}), 404
            
        new_resume = UserResume(
            user_id=current_user.id,
            title=new_title,
            theme=orig.theme,
            content_json=orig.content_json,
            ats_score=orig.ats_score
        )
        db.session.add(new_resume)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Version duplicated!", "id": new_resume.id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@features_bp.route('/resume-analyzer/share-link', methods=['POST'])
@login_required
def share_link():
    try:
        data = request.get_json() or {}
        resume_id = data.get('id')
        if not resume_id:
            return jsonify({"success": False, "error": "Resume ID required"}), 400
            
        resume = UserResume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not resume:
            return jsonify({"success": False, "error": "Resume not found"}), 404
            
        share_url = url_for('features.shared_resume', resume_id=resume.id, _external=True)
        return jsonify({"success": True, "share_url": share_url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@features_bp.route('/resume-analyzer/shared/<int:resume_id>', methods=['GET'])
@features_bp.route('/published-portfolio/shared/<int:resume_id>', methods=['GET'])
def shared_resume(resume_id):
    resume = UserResume.query.get_or_404(resume_id)
    try:
        content = json.loads(resume.content_json)
    except Exception:
        content = {}
    return render_template('public_resume.html', resume=resume, content=content)

