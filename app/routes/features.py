import os
import io
import re
import json
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models import db, User, ChatMessage, ResumeAnalysis, RoadmapProgress, UserResume
from pypdf import PdfReader

features_bp = Blueprint('features', __name__)

# --- GEMINI CLIENT WRAPPER ---
def call_gemini(system_prompt: str, user_prompt: str, user_key: str = None) -> str:
    api_key = user_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "" # Trigger mock fallback
        
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
    
    return {
        "atsScore": score,
        "readabilityScore": readability,
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
        
        "projectTitle": "AegisShield AI – Cyber Crime Detection Platform",
        "projectLink": "github.com/alexsmith/aegisshield-ai",
        "projectB1": "",
        "projectB2": "",
        "projectB3": "",
        
        "certC1": "",
        "certC2": "",
        "certC3": "",
        "certC4": ""
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
                {"title": f"Microsoft Learn: {theme} Introduction", "url": "https://learn.microsoft.com"},
                {"title": f"GitHub Repository Template for {theme}", "url": "https://github.com"}
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
            }]
        })
        
    return nodes

# --- ROUTES CONTROLLERS ---

# 1. Learning Roadmaps
@features_bp.route('/roadmaps', methods=['GET'])
@login_required
def list_roadmaps():
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
        "Robotics", "IoT", "Embedded Systems", "Database Engineering",
        "Site Reliability Engineering", "Business Analysis", "SAP", "Salesforce", "Competitive Programming"
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
        
    fields = parse_text_to_resume_fields(extracted_text)
    analysis = heuristic_parse_resume(extracted_text)
    
    new_analysis = ResumeAnalysis(
        user_id=current_user.id,
        filename=filename,
        ats_score=analysis['atsScore'],
        readability_score=analysis['readabilityScore'],
        industry_match_score=analysis['industryMatchScore'],
        target_role="Software Engineer",
        analysis_json=json.dumps(analysis)
    )
    db.session.add(new_analysis)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": fields,
        "score": analysis['atsScore'],
        "readability": analysis['readabilityScore'],
        "alignment": analysis['industryMatchScore'],
        "feedback": {
            "score": analysis['atsScore'],
            "missingKeywords": analysis['missingKeywords'],
            "improvements": analysis['improvements'],
            "mistakes": analysis['mistakes'],
            "suggestions": analysis['suggestions']
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

# 3. AI Chatbot / AI Mentor
@features_bp.route('/ai-mentor', methods=['GET'])
@login_required
def ai_mentor():
    history = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.asc()).all()
    return render_template('ai_mentor.html', history=history)

@features_bp.route('/ai-mentor/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json() or {}
    message_content = data.get('message', '').strip()
    custom_key = data.get('custom_key', '').strip()
    
    if not message_content:
        return jsonify({"success": False, "error": "Message is required"}), 400
        
    # Rate limiting check: enforce 3 seconds delay between messages
    last_msg = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.desc()).first()
    if last_msg:
        delta = datetime.utcnow() - last_msg.created_at
        if delta.total_seconds() < 3.0:
            return jsonify({
                "success": False, 
                "error": "Rate limit exceeded. Please wait 3 seconds between messages."
            }), 429

        
    # 1. Command Center Keywords Interceptor
    message_lower = message_content.lower()
    command_response = None
    
    if "create roadmap for" in message_lower or "generate roadmap for" in message_lower or "create track for" in message_lower:
        parts = message_content.split("for")
        track_part = parts[-1].strip().strip("!.")
        
        all_tracks = [
            "Cyber Security", "Ethical Hacking", "SOC Analyst", "Digital Forensics",
            "AI Engineering", "Machine Learning", "Deep Learning", "Generative AI", "Prompt Engineering", "Agentic AI",
            "Data Science", "Data Analytics", "Python Developer", "Java Developer", "C++ Developer",
            "Full Stack Development", "Frontend Development", "Backend Development", "React Developer", "Node.js Developer",
            "Mobile App Development", "Android Development", "Flutter Development",
            "Cloud Computing", "AWS", "Azure", "Google Cloud",
            "DevOps", "Kubernetes", "Docker", "Linux Engineering", "Network Engineering",
            "Blockchain", "Web3", "UI/UX Design", "Product Design", "Product Management",
            "Software Testing", "QA Automation", "Game Development", "AR/VR Development",
            "Robotics", "IoT", "Embedded Systems", "Database Engineering",
            "Site Reliability Engineering", "Business Analysis", "SAP", "Salesforce", "Competitive Programming"
        ]
        
        matched_track = None
        for t in all_tracks:
            if t.lower() in track_part.lower() or track_part.lower() in t.lower():
                matched_track = t
                break
                
        if not matched_track:
            matched_track = track_part.title()
            
        progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
        if not progress:
            progress = RoadmapProgress(user_id=current_user.id, role=matched_track, completed_nodes="")
            db.session.add(progress)
        else:
            progress.role = matched_track
            progress.completed_nodes = ""
        db.session.commit()
        
        command_response = (
            f"🎯 **Command Center Triggered: Track Seeding**\n\n"
            f"I have initialized and seeded your active learning pathway to **{matched_track}**!\n\n"
            f"The learning engine generated a visual tree containing 200 checkpoints, custom practice projects, and Microsoft Learn resources.\n\n"
            f"👉 [Click here to view your new Roadmap](/roadmaps)"
        )
        
    elif "improve resume" in message_lower or "analyze resume" in message_lower or "check resume" in message_lower or "resume score" in message_lower:
        command_response = (
            f"📝 **Command Center Triggered: Resume Analysis**\n\n"
            f"I have loaded the resume analyzer module settings.\n\n"
            f"You can upload your PDF or DOCX file, check real-time ATS scores, compare before/after modifications, and get keywords checklist suggestions.\n\n"
            f"👉 [Click here to access Resume Builder 3.0](/resume-analyzer)"
        )
        
    elif "mock interview" in message_lower or "practice interview" in message_lower or "interview simulator" in message_lower:
        command_response = (
            f"🎙️ **Command Center Triggered: Interview Simulator**\n\n"
            f"I have prepared the technical and HR interview simulator.\n\n"
            f"Test your real-time responses with local Web Speech API text-to-speech feedback, score metrics, and FAANG level questions.\n\n"
            f"👉 [Click here to start the AI Interview Simulator](/interview-simulator)"
        )
        
    elif "portfolio builder" in message_lower or "generate portfolio" in message_lower or "create website" in message_lower:
        command_response = (
            f"🌐 **Command Center Triggered: Portfolio Generator**\n\n"
            f"Let's build a stunning responsive HTML portfolio website based on your profile details.\n\n"
            f"Click the link below to generate, preview, and download your personal website code with one click.\n\n"
            f"👉 [Click here to access AI Portfolio Builder](/portfolio-builder)"
        )
        
    elif "project architect" in message_lower or "design database" in message_lower or "folders structure" in message_lower:
        command_response = (
            f"🏗️ **Command Center Triggered: Project Architect**\n\n"
            f"I have loaded the project blueprint blueprinting engine.\n\n"
            f"Generate database schemas, file tree layouts, and configurations for Node.js, Python, or Web projects instantly.\n\n"
            f"👉 [Click here to use AI Project Architect](/project-architect)"
        )
        
    elif "internship center" in message_lower or "apply internships" in message_lower or "check openings" in message_lower:
        command_response = (
            f"💼 **Command Center Triggered: Internship Matcher**\n\n"
            f"I have processed the live student internships catalog.\n\n"
            f"Review available roles matched with your current branch and year, and see your customized AI eligibility ranking details.\n\n"
            f"👉 [Click here to browse the Internship Center](/internship-center)"
        )
        
    elif "help" == message_lower or "commands" == message_lower:
        command_response = (
            f"🤖 **CampusMate AI Chat Command Center**\n\n"
            f"You can use these shortcut keywords directly in chat to operate features:\n"
            f"- `create roadmap for [Track]` (e.g. `create roadmap for Web3`)\n"
            f"- `improve resume` or `analyze resume`\n"
            f"- `mock interview` or `practice interview`\n"
            f"- `portfolio builder` or `generate portfolio`\n"
            f"- `project architect` or `design database`\n"
            f"- `internship center` or `apply internships`"
        )

    if command_response:
        # Save user message to database
        user_msg = ChatMessage(user_id=current_user.id, sender='user', content=message_content)
        db.session.add(user_msg)
        # Save command response to database
        ai_msg = ChatMessage(user_id=current_user.id, sender='ai', content=command_response)
        db.session.add(ai_msg)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "response": command_response
        })

    # Get user profile information to form a context system prompt
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    role = progress.role if progress else "Not Selected"
    history = ResumeAnalysis.query.filter_by(user_id=current_user.id).order_by(ResumeAnalysis.created_at.desc()).first()
    resume_grade = f"{history.ats_score}/100" if history else "No Resume Uploaded"
    
    system_prompt = (
        f"You are CampusMate AI, a professional academic advisor and career coach. "
        f"The student's details are: Username: {current_user.username}, Email: {current_user.email}, "
        f"Academic Level: {current_user.role.upper()}, Target Track: {role}, "
        f"Latest Resume score: {resume_grade}. "
        f"Answer the student's career, homework, coding, and resume questions professionally. "
        f"Keep your responses clean, helpful, formatting in crisp markdown. Avoid overly generic advice."
    )
    
    # Save user message to database
    user_msg = ChatMessage(user_id=current_user.id, sender='user', content=message_content)
    db.session.add(user_msg)
    db.session.commit()
    
    # Call Gemini API
    ai_response_content = call_gemini(system_prompt, message_content, user_key=custom_key)
    
    # Fallback to intelligent mock response if Gemini fails or API key is not configured
    if not ai_response_content:
        ai_response_content = (
            f"🤖 *[Mode: Sandbox Offline Mode / API Key Not Found]*\n\n"
            f"Hello {current_user.username}! I am operating in Sandbox mode since no valid `GEMINI_API_KEY` was found in the environment variables, "
            f"and no user key was entered in your sidebar settings.\n\n"
            f"**Here is your advice regarding '{message_content}':**\n"
            f"- For **{role}** tracks, make sure you complete your milestones sequentially and practice the Capstone projects.\n"
            f"- Make sure to verify your Resume Analyzer checklist to fix any formatting errors and missing keywords.\n"
            f"- Focus on learning modern tools like Docker, Git, and REST API frameworks to build dynamic SaaS applications."
        )
        
    # Save AI response to database
    ai_msg = ChatMessage(user_id=current_user.id, sender='ai', content=ai_response_content)
    db.session.add(ai_msg)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "response": ai_response_content
    })

@features_bp.route('/ai-mentor/history', methods=['GET'])
@login_required
def ai_mentor_history():
    messages = ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.asc()).all()
    history = [{"sender": m.sender, "content": m.content} for m in messages]
    
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    track = progress.role if progress else "None selected"
    
    completed_count = 0
    if progress and progress.completed_nodes:
        completed_count = len([x for x in progress.completed_nodes.split(",") if x.strip()])
    xp = 100 + completed_count * 20
    
    resume = ResumeAnalysis.query.filter_by(user_id=current_user.id).order_by(ResumeAnalysis.created_at.desc()).first()
    resume_score = resume.ats_score if resume else 0
    
    return jsonify({
        "history": history,
        "track": track,
        "xp": xp,
        "resume_score": resume_score
    })

@features_bp.route('/ai-mentor/reset', methods=['POST'])
@login_required
def ai_mentor_reset():
    ChatMessage.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"success": True})

# 4. AJAX Resume Analysis (Side-by-side Builder Verification)
@features_bp.route('/resume-analyzer/analyze', methods=['POST'])
@login_required
def analyze_resume_ajax():
    data = request.get_json() or {}
    
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
    
    analysis = heuristic_parse_resume(full_text)
    
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    target_role = progress.role if progress else "Software Engineer"
    analysis['target_role'] = target_role
    
    new_analysis = ResumeAnalysis(
        user_id=current_user.id,
        filename=data.get('title', 'Scratch_Resume_Version'),
        ats_score=analysis['atsScore'],
        readability_score=analysis['readabilityScore'],
        industry_match_score=analysis['industryMatchScore'],
        target_role=target_role,
        analysis_json=json.dumps(analysis)
    )
    db.session.add(new_analysis)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "score": analysis['atsScore'],
        "readability": analysis['readabilityScore'],
        "alignment": analysis['industryMatchScore'],
        "feedback": {
            "score": analysis['atsScore'],
            "missingKeywords": analysis['missingKeywords'],
            "improvements": analysis['improvements'],
            "mistakes": analysis['mistakes'],
            "suggestions": analysis['suggestions']
        }
    })

# 5. Interview Prep
@features_bp.route('/interview-prep', methods=['GET'])
@login_required
def interview_prep():
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    user_track = progress.role if progress else "Full Stack Development"
    return render_template('interview_prep.html', user_track=user_track)

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

# 6. Hackathon Assistant
@features_bp.route('/hackathon-assistant', methods=['GET'])
@login_required
def hackathon_assistant():
    return render_template('hackathon.html')

@features_bp.route('/hackathon-assistant/generate', methods=['POST'])
@login_required
def hackathon_generate():
    data = request.get_json() or {}
    theme = data.get('theme', '')
    custom_key = data.get('custom_key', '').strip()
    
    if not theme:
        return jsonify({"success": False, "error": "Theme is required"}), 400
        
    system_prompt = (
        "You are a Hackathon Mentor. Draft a comprehensive project MVP blueprint concept for the theme provided. "
        "Format your response in structured HTML matching the expected outline: "
        "1. MVP Architecture Overview (wrap architecture diagrams in <pre><code>...</code></pre>), "
        "2. Tech Stack & Configurations (as a list), "
        "3. Presentation Pitch Outline (Slide outline list), "
        "4. Step-by-Step implementation milestones."
    )
    user_prompt = f"Hackathon Theme: {theme}"
    
    ai_res = call_gemini(system_prompt, user_prompt, user_key=custom_key)
    if not ai_res:
        ai_res = (
            f"<h2>Hackathon Project Blueprint: {theme}</h2>"
            f"<h3>1. MVP Architecture Overview</h3>"
            f"<pre><code>[Frontend: HTML5/JS] ---> [Flask App Server] ---> [SQLite Database]</code></pre>"
            f"<h3>2. Tech Stack & Library Configurations</h3>"
            f"<ul>"
            f"<li><strong>Language:</strong> Python 3.12, Javascript ES6</li>"
            f"<li><strong>Backend:</strong> Flask, SQLAlchemy (ORM)</li>"
            f"<li><strong>Styling:</strong> Vanilla CSS with layout variables</li>"
            f"</ul>"
            f"<h3>3. Presentation Pitch Outline</h3>"
            f"<ul>"
            f"<li><strong>Slide 1:</strong> Problem statement & current inefficiencies.</li>"
            f"<li><strong>Slide 2:</strong> Solution architecture & demo overview.</li>"
            f"<li><strong>Slide 3:</strong> Future roadmap & API expandability layers.</li>"
            f"</ul>"
            f"<h3>4. Implementation milestones</h3>"
            f"<p>Define schemas, configure Flask factory app, package inside Docker, and push deployments to Railway.</p>"
        )
    else:
        ai_res = ai_res.replace("### ", "<h3>").replace("## ", "<h2>").replace("\n", "<br>")
        
    return jsonify({
        "success": True,
        "response": ai_res
    })


# 7. Internship Center
@features_bp.route('/internship-center', methods=['GET'])
@login_required
def internship_center():
    progress = RoadmapProgress.query.filter_by(user_id=current_user.id).first()
    user_track = progress.role if progress else "Full Stack Development"
    
    # Mock list of internship jobs matching user profiles
    all_jobs = [
        {"title": "Software Engineer Intern", "company": "Microsoft", "track": "Full Stack Development", "stipend": "$8,500/mo", "location": "Redmond, WA (Hybrid)", "skills": "Python, React, Data Structures"},
        {"title": "AI Engineering Intern", "company": "Google DeepMind", "track": "AI Engineering", "stipend": "$9,200/mo", "location": "London, UK (On-site)", "skills": "PyTorch, Transformers, LLMs"},
        {"title": "Machine Learning Intern", "company": "Meta", "track": "Machine Learning", "stipend": "$9,000/mo", "location": "Menlo Park, CA (Hybrid)", "skills": "Scikit-Learn, PyTorch, SQL"},
        {"title": "Cyber Security Analyst Intern", "company": "CrowdStrike", "track": "Cyber Security", "stipend": "$7,500/mo", "location": "Austin, TX (Remote)", "skills": "Nmap, Wireshark, Linux Scripting"},
        {"title": "DevOps Engineer Intern", "company": "HashiCorp", "track": "DevOps", "stipend": "$7,800/mo", "location": "San Francisco, CA (Hybrid)", "skills": "Docker, Kubernetes, Terraform"},
        {"title": "Cloud Operations Intern", "company": "Amazon Web Services", "track": "Cloud Computing", "stipend": "$8,200/mo", "location": "Seattle, WA (On-site)", "skills": "AWS IAM, EC2, CloudFormation"},
        {"title": "Blockchain Developer Intern", "company": "ConsenSys", "track": "Web3", "stipend": "$8,000/mo", "location": "Remote", "skills": "Solidity, Ethereum, Smart Contracts"},
        {"title": "UI/UX Product Design Intern", "company": "Figma", "track": "UI/UX Design", "stipend": "$7,200/mo", "location": "San Francisco, CA (Hybrid)", "skills": "Figma, User Research, Wireframing"},
        {"title": "QA Automation Engineer Intern", "company": "BrowserStack", "track": "QA Automation", "stipend": "$6,500/mo", "location": "Dublin, Ireland (Hybrid)", "skills": "Selenium, Playwright, Python"},
        {"title": "Product Management Intern", "company": "Stripe", "track": "Product Management", "stipend": "$8,800/mo", "location": "New York, NY (Hybrid)", "skills": "Agile Scrum, Figma, Business Analytics"}
    ]
    
    resume = ResumeAnalysis.query.filter_by(user_id=current_user.id).order_by(ResumeAnalysis.created_at.desc()).first()
    resume_score = resume.ats_score if resume else 0
    
    jobs = []
    for idx, job in enumerate(all_jobs):
        compatibility = 40
        if user_track.lower() in job["track"].lower() or job["track"].lower() in user_track.lower():
            compatibility += 40
        compatibility += min(15, int((current_user.xp or 0) / 100))
        compatibility += min(15, int(resume_score / 10))
        compatibility = min(98, compatibility)
        
        jobs.append({
            "id": idx + 1,
            "title": job["title"],
            "company": job["company"],
            "track": job["track"],
            "stipend": job["stipend"],
            "location": job["location"],
            "skills": job["skills"],
            "compatibility": compatibility
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
    
    name = current_user.username.title()
    email = current_user.email
    branch = current_user.branch or "Computer Science"
    year = current_user.year or "3rd Year"
    track = current_user.career_goal or "Software Engineer"
    skills = current_user.skills or "Python, JavaScript, HTML/CSS, SQL"
    xp = current_user.xp
    
    projects_list = [
        {"title": "CampusMate AI Core Engine", "desc": "Built a unified student platform mapping curriculum trees and ATS feedback workflows.", "tech": "Python, Flask, SQLite"},
        {"title": "Distributed Task Scheduler", "desc": "Implemented a concurrent cron scheduler containerized with Docker and monitored via Prometheus.", "tech": "Go, Docker, Prometheus"},
        {"title": "Real-time Chat Application", "desc": "Developed a full-stack real-time messaging workspace utilizing WebSockets and Redis memory cache.", "tech": "Node.js, Express, WebSockets, Redis"}
    ]
    
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

