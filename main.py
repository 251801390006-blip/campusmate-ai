import os
import uuid
import io
import zipfile
import re
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, Security, File, UploadFile, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from pydantic import BaseModel
import bcrypt
from jose import jwt, JWTError
from pypdf import PdfReader

from database import init_db, get_session
from models import (
    User, Profile, SkillMaster, UserSkill, 
    Roadmap, RoadmapNode, Resume, UserProjectProgress, 
    LearningSession, AIConversation, AIMessage
)

# Initialize FastAPI App
app = FastAPI(
    title="CampusMate AI API",
    description="The complete AI operating system for students backend.",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password Hashing Setup (Using native bcrypt to fix passlib long password ValueErrors)
# Standard bcrypt is used directly to prevent passlib compatibility errors on python 3.14.

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "campusmate_ai_super_secret_dev_key_change_in_production")
ALGORITHM = "HS256"
security_bearer = HTTPBearer()

# Helper Functions for Security
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7) # 7-day token for development convenience
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
    session: Session = Depends(get_session)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials signature."
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired or is invalid."
        )
    
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found."
        )
    return user

# Gemini API Client Setup (Dynamic Fallback)
def call_gemini(system_prompt: str, user_prompt: str, user_key: Optional[str] = None) -> str:
    api_key = user_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "" # Empty indicates mock fallback should be triggered
    
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


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
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

def extract_text_from_docx_bytes(file_bytes: bytes) -> str:
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

def heuristic_parse_resume(text: str) -> Dict[str, Any]:
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
    
    # Name heuristic: first line that doesn't contain @, |, or http
    name = "Alex Smith"
    for line in lines[:5]:
        if '@' not in line and 'http' not in line and '|' not in line and len(line) < 50:
            name = line
            break
            
    # Segment text by sections
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
        elif any(h in line_lower for h in ["experience", "employment", "work history", "career", "history"]):
            current_section = "experience"
        elif any(h in line_lower for h in ["projects", "personal projects", "portfolio", "key projects"]):
            current_section = "projects"
        elif any(h in line_lower for h in ["skills", "technical skills", "languages", "technologies", "expertise"]):
            current_section = "skills"
        elif any(h in line_lower for h in ["certifications", "certs", "credentials", "achievements"]):
            current_section = "certifications"
        elif current_section:
            sections[current_section].append(line)
            
    edu1_inst = ""
    edu1_degree = ""
    edu1_dates = ""
    edu1_gpa = ""
    edu1_coursework = ""
    
    edu2_inst = ""
    edu2_degree = ""
    edu2_dates = ""
    edu2_gpa = ""
    
    if sections["education"]:
        edu1_inst = sections["education"][0]
        if len(sections["education"]) > 1:
            edu1_degree = sections["education"][1]
        for line in sections["education"]:
            if "gpa" in line.lower() or "cgpa" in line.lower():
                edu1_gpa_match = re.search(r'\b\d\.\d{1,2}\b', line)
                if edu1_gpa_match:
                    edu1_gpa = edu1_gpa_match.group(0)
            if any(m in line.lower() for m in ["202", "201", "200", "present"]):
                edu1_dates = line
                
    skills_prog = ""
    skills_cyber = ""
    skills_os = ""
    skills_tools = ""
    skills_web = ""
    
    all_skills_text = " ".join(sections["skills"]) if sections["skills"] else text
    
    prog_keywords = ["python", "javascript", "typescript", "java", "c++", "c#", "rust", "go", "ruby", "php"]
    cyber_keywords = ["wireshark", "nmap", "metasploit", "penetration testing", "cybersecurity", "firewall", "snort", "cryptography"]
    os_keywords = ["linux", "windows", "macos", "ubuntu", "debian", "redhat", "centos"]
    tools_keywords = ["git", "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "jenkins", "ansible"]
    web_keywords = ["react", "vue", "angular", "fastapi", "django", "flask", "node", "express", "html", "css"]
    
    found_prog = [k.capitalize() for k in prog_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    found_cyber = [k.capitalize() for k in cyber_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    found_os = [k.capitalize() for k in os_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    found_tools = [k.capitalize() for k in tools_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    found_web = [k.capitalize() for k in web_keywords if re.search(r'\b' + re.escape(k) + r'\b', all_skills_text, re.IGNORECASE)]
    
    skills_prog = ", ".join(found_prog)
    skills_cyber = ", ".join(found_cyber)
    skills_os = ", ".join(found_os)
    skills_tools = ", ".join(found_tools)
    skills_web = ", ".join(found_web)
    
    exp_role = "Software Engineering Intern"
    exp_comp = "Global Tech Solutions"
    exp_dates = "June 2025 - August 2025"
    exp_b1 = ""
    exp_b2 = ""
    exp_b3 = ""
    exp_b4 = ""
    
    if sections["experience"]:
        exp_role = sections["experience"][0]
        if len(sections["experience"]) > 1:
            exp_comp = sections["experience"][1]
        
        bullets = [line for line in sections["experience"] if line.startswith(("-", "*", "•")) or len(line) > 30]
        if len(bullets) > 0: exp_b1 = bullets[0].lstrip("-*• ")
        if len(bullets) > 1: exp_b2 = bullets[1].lstrip("-*• ")
        if len(bullets) > 2: exp_b3 = bullets[2].lstrip("-*• ")
        if len(bullets) > 3: exp_b4 = bullets[3].lstrip("-*• ")
            
    proj_title = "Personal Project"
    proj_link = ""
    proj_b1 = ""
    proj_b2 = ""
    proj_b3 = ""
    
    if sections["projects"]:
        proj_title = sections["projects"][0]
        bullets = [line for line in sections["projects"] if line.startswith(("-", "*", "•")) or len(line) > 30]
        if len(bullets) > 0: proj_b1 = bullets[0].lstrip("-*• ")
        if len(bullets) > 1: proj_b2 = bullets[1].lstrip("-*• ")
        if len(bullets) > 2: proj_b3 = bullets[2].lstrip("-*• ")
            
    certs = ["", "", "", ""]
    if sections["certifications"]:
        for i, line in enumerate(sections["certifications"][:4]):
            certs[i] = line.lstrip("-*• ")
            
    score = 50
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
    
    readability = min(60 + len(found_verbs) * 3 + (10 if len(lines) > 20 else 0), 95)
    industry_match = min(50 + len(found_prog + found_cyber + found_tools + found_web) * 3, 96)
    
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
            "suggestedText": "Architected performant relational database schemas and API routing structures in FastAPI, reducing API controller latency by 20%.",
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
        "success": True,
        "filename": "Uploaded_Resume",
        "atsScore": score,
        "readabilityScore": readability,
        "industryMatchScore": industry_match,
        "content": {
            "name": name,
            "address": "San Francisco, California, USA",
            "email": email or "student@campusmate.edu",
            "phone": phone or "+1 (555) 019-2834",
            "linkedin": linkedin or "linkedin.com/in/student",
            "github": github or "https://github.com/student",
            "edu1Inst": edu1_inst or "State University",
            "edu1Degree": edu1_degree or "Bachelor of Science in Computer Science",
            "edu1Dates": edu1_dates or "2022 - 2026",
            "edu1Gpa": edu1_gpa or "3.8",
            "edu1Coursework": "Data Structures, Database Management, Software Engineering",
            "edu2Inst": edu2_inst,
            "edu2Degree": edu2_degree,
            "edu2Dates": edu2_dates,
            "edu2Gpa": edu2_gpa,
            "skillsProg": skills_prog or "Python, JavaScript",
            "skillsCyber": skills_cyber or "Vulnerability Assessment",
            "skillsOs": skills_os or "Linux",
            "skillsTools": skills_tools or "Git, Docker",
            "skillsWeb": skills_web or "FastAPI, React",
            "experienceRole": exp_role,
            "experienceComp": exp_comp,
            "experienceDates": exp_dates,
            "experienceB1": exp_b1 or "Contributed to design and development of system modules.",
            "experienceB2": exp_b2 or "Implemented secure coding practices and automated configurations.",
            "experienceB3": exp_b3 or "Supported data migration and JWT authentication setups.",
            "experienceB4": exp_b4,
            "projectTitle": proj_title,
            "projectLink": proj_link or "github.com/student/project",
            "projectB1": proj_b1 or "Developed key features and functionalities for the platform.",
            "projectB2": proj_b2 or "Configured and maintained local environment configs.",
            "projectB3": proj_b3,
            "certC1": certs[0] or "Professional Certificate in IT Fundamentals",
            "certC2": certs[1],
            "certC3": certs[2],
            "certC4": certs[3]
        },
        "feedback": {
            "score": score,
            "missingKeywords": missing_keywords,
            "improvements": improvements,
            "mistakes": mistakes,
            "suggestions": suggestions
        }
    }

def get_predefined_roadmap(role: str) -> List[Dict[str, Any]]:
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
            ("Purple Teaming & Incident Response", "Collaborate on attack/defense simulations and incident reporting.")
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
            ("Exposing Models via FastAPI Docker", "Wrap model inference scripts inside FastAPI and run via Docker.")
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
            ("Advanced Hyperparameter Search", "Run Optuna, grid searches, and optimize batch size metrics.")
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
            ("Capstone: Interactive Data Dashboard", "Deliver a comprehensive project featuring clean ETL and plots.")
        ]
        provider = "Microsoft / Databricks"
        cert = "Microsoft Certified: Power BI Data Analyst Associate"
    # 5. Cloud Computing
    elif "cloud" in role_lower:
        milestones = [
            ("Cloud Computing Fundamentals", "Learn IaaS, PaaS, SaaS, and public vs private structures."),
            ("Virtual Machines & OS Provisioning", "Spin up VMs, configure SSH access, and update repositories."),
            ("Virtual Networking & Subnetting", "Deploy virtual networks, design subnets, and configure routes."),
            ("Firewalls & Network Access Control", "Configure ingress/egress rules and block open SSH ports."),
            ("Cloud Object Storage Essentials", "Create storage buckets, configure access controls, and files."),
            ("IAM: Users, Groups & Policy JSON", "Write strict access policies and delegate privileges safely."),
            ("SQL Databases in the Cloud", "Provision relational instances and audit connectivity links."),
            ("NoSQL Cloud Database Engines", "Setup key-value engines and configure primary partition keys."),
            ("Load Balancers & High Availability", "Distribute HTTP requests across target server pools."),
            ("Auto-Scaling & Elastic Operations", "Configure rules to automatically scale node counts on load."),
            ("Serverless Functions (FaaS)", "Deploy event-driven functions and configure trigger endpoints."),
            ("DNS Routing & Domain Registries", "Configure target routes, health checks, and domain maps."),
            ("Content Delivery Networks (CDN)", "Cache static images and CSS stylesheets at edge locations."),
            ("Monitoring, Metrics & Logs Tracker", "Setup metric graphs and track CPU/memory alerts."),
            ("Backup, Restore & Disaster Recovery", "Schedule snapshot policies and test database recovery loops."),
            ("Terraform: Infrastructure as Code (IaC)", "Define VMs, networks, and firewalls using YAML/HCL configurations."),
            ("Terraform: State Files & Variables", "Manage state configs, output parameters, and modules."),
            ("Cloud Container Registry setups", "Build Docker images and push to cloud registry stores."),
            ("Kubernetes Cloud Clusters (EKS/AKS)", "Provision managed Kubernetes clusters and connect kubectl."),
            ("Hybrid Cloud & VPN Tunnel Gateway", "Bridge local data networks to cloud nodes using secure VPNs."),
            ("Cloud Billing & Cost Controls", "Set spending limits, configure alarms, and clean unused disks."),
            ("Shared Responsibility Security Audits", "Evaluate vulnerability logs, WAF alerts, and security groups."),
            ("Automated VM Configuration (Ansible)", "Write playbooks to deploy web servers on fresh cloud VMs."),
            ("Server Migration Strategies", "Learn how to lift and shift database nodes to cloud instances."),
            ("Capstone: Deploy Secure Cloud Cluster", "Deploy a complete SaaS network behind load balancers with WAF.")
        ]
        provider = "Amazon AWS / Microsoft"
        cert = "AWS Certified Solutions Architect – Associate"
    # 6. DevOps
    elif "devops" in role_lower:
        milestones = [
            ("DevOps Culture & Linux Shell Power", "Learn standard commands, file management, and terminal tools."),
            ("Git Foundations & Branching Models", "Master merging, rebasing, pull requests, and git-flow patterns."),
            ("Bash Scripting & Automation Loops", "Write automation scripts to clean temp files and parse logs."),
            ("Docker: Building Custom Containers", "Write Dockerfiles, configure layers, and run entrypoints."),
            ("Docker Compose: Multi-Container Setup", "Run backend APIs and database nodes side-by-side using YAML."),
            ("Docker Volumes & Persistent Storage", "Configure mount volumes and preserve data across restarts."),
            ("CI/CD: GitHub Actions Workflows", "Create YAML workflows to compile code on push events."),
            ("CI/CD: Automated Linter & Unit Tests", "Integrate automated check steps and block broken pull builds."),
            ("Infrastructure as Code (IaC) Basics", "Learn declarative config models and write simple YAML plans."),
            ("Terraform: Provisioning Local Dev Host", "Write terraform configs to deploy Docker containers."),
            ("Terraform: State Management & Backends", "Configure remote state locking to avoid resource conflicts."),
            ("Configuration Management: Ansible", "Write playbooks to configure packages on server networks."),
            ("Continuous Deployment: SSH Web Deploy", "Auto-deploy code directly to remote servers using SSH scripts."),
            ("Monitoring Systems: Prometheus Basics", "Expose metrics endpoints and monitor CPU/RAM utilization."),
            ("Log Aggregation: ELK Stack / Grafana", "Collect application logs, construct dashboards, and monitor errors."),
            ("Kubernetes: Pods, Services & Deployments", "Write YAML manifests to deploy container sets locally."),
            ("Kubernetes: ConfigMaps & Secrets", "Inject environment variables and secret tokens securely."),
            ("Kubernetes: Ingress & Domain Routing", "Deploy ingress controllers to route HTTP traffic to services."),
            ("Helm: Packaging Kubernetes Apps", "Use Helm charts to install persistent database clusters."),
            ("GitOps: Intro to ArgoCD pipelines", "Sync Kubernetes clusters directly with git repository state."),
            ("SaaS Logging & Alerting Triggers", "Setup Slack/email alert webhooks for down server nodes."),
            ("CI/CD: Artifact Registries & Packages", "Publish compiled images to secure image registries."),
            ("Security: Scanning Docker Images (Trivy)", "Integrate CVE vulnerability scans inside build jobs."),
            ("DevSecOps: Secret Key Scanning", "Audit repository histories and block commit keys from git."),
            ("Capstone: Zero-Downtime CD Pipeline", "Deliver an automated pipeline that builds, tests, and rolls updates.")
        ]
        provider = "HashiCorp / RedHat"
        cert = "HashiCorp Certified: Terraform Associate"
    # 7. Full Stack
    elif "full" in role_lower or "web" in role_lower or "developer" in role_lower or "engineering" in role_lower or "software" in role_lower:
        milestones = [
            ("Internet Basics & Web Architectures", "Understand HTTP protocols, DNS servers, and request lifecycles."),
            ("Semantic HTML5 Document Design", "Learn layout structures, inputs, buttons, and document trees."),
            ("CSS3 Styling: Flexbox & Page Grids", "Align interface cards, configure grid spans, and margins."),
            ("Responsive CSS Variables & Queries", "Build responsive layouts using variables and media queries."),
            ("Modern Styling: Brutalist & Glassmorphism", "Apply neo-brutalist solid black borders and glass cards."),
            ("JavaScript Variables, Arrays & loops", "Master basic data handling, loops, and conditions."),
            ("DOM Manipulation & Page Events", "Write event listeners to dynamically modify page elements."),
            ("JavaScript Promises & Async/Await", "Fetch JSON payloads from backend endpoints asynchronously."),
            ("React: Creating Functional Components", "Learn components, props, and render layouts in React."),
            ("React: Hooks, State & Input Binding", "Use useState and useEffect to bind input variables."),
            ("React: Context API & Routing", "Configure app navigation tabs and global user states."),
            ("Node.js Runtime & Package Systems", "Write terminal scripts and load external modules."),
            ("Express.js REST APIs & Routing", "Configure GET/POST routes and handle JSON body payloads."),
            ("Relational Database Schema Design", "Design PostgreSQL tables, keys, and relational maps."),
            ("SQL Queries, Indexing & Joins", "Write query commands, join tables, and index query fields."),
            ("ORM integration: SQLModel / Prisma", "Map database tables to programming models."),
            ("Authentication: JWT Tokens & Hash", "Hash passwords with bcrypt and sign JWT session tokens."),
            ("API Gateways, CORS & Rate Limiting", "Secure endpoints from unauthorized cross-origin requests."),
            ("Unit Testing Backend Controllers", "Write test suites, run assertions, and mock databases."),
            ("Frontend Integration & Fetch Client", "Call authentication and data endpoints from frontend pages."),
            ("Dockerizing Full Stack Applications", "Containerize frontend and backend layers into single images."),
            ("CI/CD Pipelines: Automated Release", "Configure GitHub Actions to compile and deploy to cloud hosts."),
            ("Performance: Query Caching with Redis", "Cache slow database outputs and speed up response cycles."),
            ("Real-Time Communication: WebSockets", "Build live interactive chat hubs using WebSocket listeners."),
            ("Capstone: Deploy E-Commerce Platform", "Deploy a complete app containing user auth, items, and billing.")
        ]
        provider = "FreeCodeCamp / OpenJS"
        cert = "Meta Front-End Developer Professional Certificate"
    # 8. Mobile Development
    else:
        milestones = [
            ("Mobile Ecosystems: iOS & Android", "Learn native app files, lifecycle stages, and app store rules."),
            ("Command Line Tools & Mobile SDKs", "Configure Android Studio, Xcode, simulator systems, and paths."),
            ("Dart / Kotlin Language Foundations", "Master variables, loops, classes, and types of native languages."),
            ("Functions & Modular File Imports", "Create reusable files, helper scripts, and async modules."),
            ("UI Layout: Widgets & Layout Grids", "Deploy layout cards, flex lists, columns, and margins."),
            ("Mobile Styling, Themes & Colors", "Apply light/dark mode support, responsive fonts, and buttons."),
            ("State Management: Local Page States", "Track text inputs, form selections, and local toggle variables."),
            ("Handling User Events: Gestures & Inputs", "Capture taps, swipes, long presses, and input focus changes."),
            ("HTTP API Integration: Networking", "Fetch data from REST APIs, decode JSON, and handle connection errors."),
            ("Local Database Storage (SQLite/Hive)", "Persist user settings and catalog local records offline."),
            ("Mobile Authentication: JWT & OAuth", "Securely store login tokens and manage user sessions."),
            ("Navigation Architectures: Tab Routers", "Configure stack navigation, tab bars, and back buttons."),
            ("Camera, Files & Device Permissions", "Request access to camera features and load local photos."),
            ("Location Services & Map Rendering", "Fetch GPS coordinates and render locations on map widgets."),
            ("Push Notifications & Background Jobs", "Setup notification triggers and sync data in the background."),
            ("Responsive UI for Mobile & Tablets", "Scale padding, layouts, and image assets dynamically."),
            ("Global State Management (Bloc/Redux)", "Share user profiles and roadmaps across different screens."),
            ("Unit & Widget UI Testing", "Write assertions for widget render states and test logic blocks."),
            ("CI/CD: Building Release Bundles", "Auto-compile APK/IPA builds and run checks using CLI tools."),
            ("App Optimizations: Caching & Loading", "Optimize image download sizes and cache local JSON records."),
            ("Google Play & Apple Store Deployment", "Publish production builds to developer testing tracks."),
            ("Error Logging & Crashlytics", "Integrate crash detectors and monitor runtime stack traces."),
            ("Animations: Transitions & Micro-actions", "Add page transitions and micro-interactions for items."),
            ("Securing App Files & Keystore Storage", "Encrypt API key tokens and secure password files in keychains."),
            ("Capstone Mobile App Deployment", "Deploy a fully functional React Native/Flutter app containing auth and maps.")
        ]
        provider = "Google / Apple"
        cert = "Google Associate Android Developer"
        
    nodes = []
    for i, (title, desc) in enumerate(milestones):
        diff = "BEGINNER" if i < 8 else ("INTERMEDIATE" if i < 17 else "ADVANCED")
        dur = f"{8 + (i % 5)*2} hours"
        nodes.append({
            "title": f"Step {i+1}: {title}",
            "description": desc,
            "estimated_duration": dur,
            "difficulty": diff,
            "resources": [{"title": f"Official documentation for {title}", "url": "https://learn.microsoft.com"}],
            "projects": [{"title": f"Implementation Project - Step {i+1}", "description": f"Build a practical system that demonstrates deep knowledge of {title}.", "tasks": ["Configure the framework settings", "Write code files implementation", "Verify local test suits passes"]}],
            "certifications": [{"name": cert, "provider": provider}]
        })
    return nodes

# API Request Models
class UserRegister(BaseModel):
    email: str
    password: str
    fullName: str
    academicLevel: str = "UNDERGRADUATE"

class UserLogin(BaseModel):
    email: str
    password: str

class ProfileUpdate(BaseModel):
    fullName: Optional[str] = None
    academicLevel: Optional[str] = None
    institution: Optional[str] = None
    targetRole: Optional[str] = None

class RoadmapGenerateRequest(BaseModel):
    targetRole: str
    skills: List[str]

class NodeStatusUpdate(BaseModel):
    status: str # LOCKED, AVAILABLE, IN_PROGRESS, COMPLETED

class ResumeSaveRequest(BaseModel):
    title: str
    theme: str
    content: Dict[str, Any]

class ResumeAnalyzeRequest(BaseModel):
    targetJobDescription: str

class MentorChatRequest(BaseModel):
    message: str

# Startup Events
@app.on_event("startup")
def on_startup():
    init_db()

# --- AUTH ROUTES ---

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, session: Session = Depends(get_session)):
    # Check if user already exists
    existing = session.exec(select(User).where(User.email == data.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered.")
    
    user_id = str(uuid.uuid4())
    new_user = User(
        id=user_id,
        email=data.email,
        password_hash=hash_password(data.password),
        role="STUDENT"
    )
    new_profile = Profile(
        user_id=user_id,
        full_name=data.fullName,
        academic_level=data.academicLevel,
        streak_count=1,
        total_xp=100,
        last_active_date=date.today()
    )
    
    session.add(new_user)
    session.add(new_profile)
    session.commit()
    
    token = create_access_token(user_id, data.email)
    return {"success": True, "token": token}

@app.post("/api/auth/login")
def login(data: UserLogin, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password.")
    
    # Update active streak
    profile = session.get(Profile, user.id)
    if profile:
        today = date.today()
        if profile.last_active_date:
            delta = today - profile.last_active_date
            if delta.days == 1:
                profile.streak_count += 1
            elif delta.days > 1:
                profile.streak_count = 1
        else:
            profile.streak_count = 1
        profile.last_active_date = today
        session.add(profile)
        session.commit()

    token = create_access_token(user.id, user.email)
    return {"success": True, "token": token}

@app.get("/api/auth/me")
def get_me(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    profile = session.get(Profile, user.id)
    return {
        "id": user.id,
        "email": user.email,
        "fullName": profile.full_name if profile else "",
        "academicLevel": profile.academic_level if profile else "UNDERGRADUATE",
        "institution": profile.institution if profile else "",
        "targetRole": profile.target_role if profile else None,
        "streak": profile.streak_count if profile else 0,
        "xp": profile.total_xp if profile else 0
    }

@app.put("/api/auth/profile")
def update_profile(
    data: ProfileUpdate, 
    user: User = Depends(get_current_user), 
    session: Session = Depends(get_session)
):
    profile = session.get(Profile, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found.")
    
    if data.fullName is not None:
        profile.full_name = data.fullName
    if data.academicLevel is not None:
        profile.academic_level = data.academicLevel
    if data.institution is not None:
        profile.institution = data.institution
    if data.targetRole is not None:
        profile.target_role = data.targetRole
        
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return {"success": True, "profile": profile}

# --- ROADMAP ROUTES ---

@app.post("/api/roadmaps/generate")
def generate_roadmap(
    data: RoadmapGenerateRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Disable previous active roadmaps
    old_roadmaps = session.exec(select(Roadmap).where(Roadmap.user_id == user.id, Roadmap.is_active == True)).all()
    for r in old_roadmaps:
        r.is_active = False
        session.add(r)
    
    roadmap_id = str(uuid.uuid4())
    new_roadmap = Roadmap(
        id=roadmap_id,
        user_id=user.id,
        title=f"{data.targetRole} Dynamic Learning Pathway",
        target_role=data.targetRole,
        is_active=True
    )
    session.add(new_roadmap)
    
    # Save target role in profile
    profile = session.get(Profile, user.id)
    if profile:
        profile.target_role = data.targetRole
        session.add(profile)

    user_key = request.headers.get("X-Gemini-API-Key")
    system_prompt = "You are a software architect that outputs roadmaps strictly in JSON format. Do not write text before or after."
    user_prompt = f"Create a learning roadmap for target role: '{data.targetRole}' with current skills: {data.skills}. Output an array of exactly 25 sequential milestone nodes. Each node must have: 'title', 'description', 'estimated_duration', 'difficulty' ('BEGINNER', 'INTERMEDIATE', 'ADVANCED'), and list of 'resources' [{{'title': ..., 'url': ...}}], 'projects' [{{'title': ..., 'description': ..., 'tasks': [...]}}], 'certifications' [{{'name': ..., 'provider': ...}}]."
    
    nodes_data = []
    if user_key or os.environ.get("GEMINI_API_KEY"):
        raw_response = call_gemini(system_prompt, user_prompt, user_key=user_key)
        if raw_response:
            try:
                import json
                cleaned = raw_response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:-3]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:-3]
                nodes_data = json.loads(cleaned.strip())
            except Exception as e:
                print(f"Failed to parse gemini JSON roadmap: {e}")
                nodes_data = []

    # Fallback to predefined 25-milestone roadmap if API key is not set or failed
    if not nodes_data:
        nodes_data = get_predefined_roadmap(data.targetRole)

    # Insert nodes into database
    parent_id = None
    for index, nd in enumerate(nodes_data):
        node_id = str(uuid.uuid4())
        status_val = "AVAILABLE" if index == 0 else "LOCKED"
        new_node = RoadmapNode(
            id=node_id,
            roadmap_id=roadmap_id,
            parent_node_id=parent_id,
            title=nd.get("title", f"Milestone {index+1}"),
            description=nd.get("description", ""),
            difficulty=nd.get("difficulty", "BEGINNER"),
            estimated_duration=nd.get("estimated_duration", "10 hours"),
            resources=nd.get("resources", []),
            projects=nd.get("projects", []),
            certifications=nd.get("certifications", []),
            status=status_val
        )
        session.add(new_node)
        parent_id = node_id
    
    session.commit()
    return {"success": True, "roadmapId": roadmap_id}

@app.get("/api/roadmaps/active")
def get_active_roadmap(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    roadmap = session.exec(
        select(Roadmap).where(Roadmap.user_id == user.id, Roadmap.is_active == True)
    ).first()
    if not roadmap:
        return {"roadmap": None, "nodes": []}
    
    nodes = session.exec(
        select(RoadmapNode).where(RoadmapNode.roadmap_id == roadmap.id)
    ).all()
    
    sorted_nodes = []
    nodes_by_parent = {n.parent_node_id: n for n in nodes}
    
    curr_parent = None
    for _ in range(len(nodes)):
        if curr_parent in nodes_by_parent:
            n = nodes_by_parent[curr_parent]
            sorted_nodes.append(n)
            curr_parent = n.id
        else:
            break
            
    for n in nodes:
        if n not in sorted_nodes:
            sorted_nodes.append(n)

    return {
        "roadmap": roadmap,
        "nodes": sorted_nodes
    }

@app.patch("/api/roadmaps/nodes/{node_id}/status")
def update_node_status(
    node_id: str,
    data: NodeStatusUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    node = session.get(RoadmapNode, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Roadmap node not found.")
    
    node.status = data.status
    node.updated_at = datetime.utcnow()
    session.add(node)
    
    if data.status == "COMPLETED":
        profile = session.get(Profile, user.id)
        if profile:
            profile.total_xp += 100
            session.add(profile)
            
        child = session.exec(
            select(RoadmapNode).where(RoadmapNode.parent_node_id == node_id)
        ).first()
        if child and child.status == "LOCKED":
            child.status = "AVAILABLE"
            session.add(child)
            
    session.commit()
    return {"success": True}

# --- RESUME ROUTES ---

@app.get("/api/resumes")
def get_user_resumes(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    res = session.exec(select(Resume).where(Resume.user_id == user.id)).all()
    return {"resumes": res}

@app.post("/api/resumes")
def save_resume(
    data: ResumeSaveRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    existing = session.exec(select(Resume).where(Resume.user_id == user.id)).first()
    if existing:
        existing.title = data.title
        existing.theme = data.theme
        existing.content = data.content
        existing.updated_at = datetime.utcnow()
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return {"success": True, "resume": existing}
    else:
        new_resume = Resume(
            id=str(uuid.uuid4()),
            user_id=user.id,
            title=data.title,
            theme=data.theme,
            content=data.content
        )
        session.add(new_resume)
        session.commit()
        session.refresh(new_resume)
        return {"success": True, "resume": new_resume}

@app.post("/api/resumes/analyze")
def analyze_resume(
    data: ResumeAnalyzeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    resume = session.exec(select(Resume).where(Resume.user_id == user.id)).first()
    if not resume:
        raise HTTPException(status_code=400, detail="Please create and save a resume first before running analysis.")
        
    system_prompt = "You are an elite ATS resume parser. Output strictly in JSON format. Do not include markdown tags."
    user_prompt = f"Analyze this resume JSON: {resume.content} against target job description: '{data.targetJobDescription}'. Return a JSON with: 'score' (0-100), 'missingKeywords' (list of missing skills), 'improvements' (list of {{'originalText', 'suggestedText', 'reason'}}), 'mistakes' (list of strings explaining exact mistakes in formatting or phrasing found), and 'suggestions' (list of strings representing actionable tips to fix those mistakes)."
    
    raw_response = call_gemini(system_prompt, user_prompt)
    
    analysis_data = None
    if raw_response:
        try:
            import json
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:-3]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:-3]
            analysis_data = json.loads(cleaned.strip())
        except Exception as e:
            print(f"Failed to parse gemini JSON resume analysis: {e}")
            analysis_data = None

    if not analysis_data:
        job_lower = data.targetJobDescription.lower()
        if "cyber" in job_lower or "security" in job_lower:
            keywords = ["Wireshark", "Nmap", "Penetration Testing", "Active Directory", "Firewall Configuration"]
        elif "ai" in job_lower or "machine" in job_lower or "data" in job_lower:
            keywords = ["Pandas", "Scikit-Learn", "Model Optimization", "Deep Learning", "Docker"]
        else:
            keywords = ["RESTful APIs", "PostgreSQL Indexes", "FastAPI Middleware", "Docker Compose", "CI/CD Pipelines"]
            
        analysis_data = {
            "score": 72,
            "missingKeywords": keywords,
            "improvements": [
                {
                    "originalText": "Responsible for coding the backend of the student project application.",
                    "suggestedText": "Architected performant relational database schemas and API routing structures in FastAPI, reducing API controller latency by 20%.",
                    "reason": "Uses passive phrasing. Suggested action verbs and concrete achievement metrics."
                },
                {
                    "originalText": "Helped team build website.",
                    "suggestedText": "Collaborated with cross-functional developers to implement glassmorphic custom layout panels, increasing user engagement levels by 30%.",
                    "reason": "Weak verb definition. Replaced with active verbs and quantified engagement levels."
                }
            ],
            "mistakes": [
                "Vague/passive verb constructs used in experience description (e.g., 'Responsible for', 'Helped').",
                "Lack of quantitative outcomes/metrics to prove efficiency gains.",
                "Portfolio link references are missing complete domain paths."
            ],
            "suggestions": [
                "Replace passive phrases with strong engineering action verbs like 'Engineered', 'Optimized', or 'Automated'.",
                "Apply the Google XYZ formula to quantify your achievements (e.g., 'increased throughput by X%').",
                "Format technical skills into distinct, scan-friendly categories."
            ]
        }

    resume.ats_score = analysis_data.get("score", 70)
    resume.recruiter_readability_score = 80
    resume.industry_match_score = 75
    resume.analysis_feedback = analysis_data
    resume.updated_at = datetime.utcnow()
    
    profile = session.get(Profile, user.id)
    if profile:
        profile.total_xp += 50
        session.add(profile)
        
    session.add(resume)
    session.commit()
    session.refresh(resume)
    
    return {"success": True, "resume": resume}


RESUME_PARSE_SYSTEM_PROMPT = """You are an expert ATS (Applicant Tracking System) parser and recruiter analyzer.
Your task is to parse the raw text of a resume and extract the key information into a structured JSON object.
You must output ONLY valid JSON. Do not write any conversational text or explanation. Do not wrap it in markdown code blocks.

Return a JSON object with the following keys:
1. "content": A dictionary containing the following keys (use empty strings if not found):
   - "name": Full name
   - "address": Address/location
   - "email": Email address
   - "phone": Phone number
   - "linkedin": LinkedIn URL or username
   - "github": GitHub URL or username
   - "edu1Inst": Primary educational institution name
   - "edu1Degree": Major/Degree name for primary education
   - "edu1Dates": Attendance dates for primary education
   - "edu1Gpa": GPA for primary education (if any)
   - "edu1Coursework": Relevant coursework for primary education
   - "edu2Inst": Secondary educational institution name (if any)
   - "edu2Degree": Major/Degree name for secondary education (if any)
   - "edu2Dates": Attendance dates for secondary education (if any)
   - "edu2Gpa": GPA for secondary education (if any)
   - "skillsProg": Programming languages/developer skills
   - "skillsCyber": Cyber security / networking skills
   - "skillsOs": Operating systems (Linux, Windows, etc.)
   - "skillsTools": Developer tools/technologies (Git, Docker, etc.)
   - "skillsWeb": Web technologies/frameworks
   - "experienceRole": Most recent job role/title
   - "experienceComp": Most recent company name
   - "experienceDates": Most recent employment dates
   - "experienceB1": First bullet point of most recent experience
   - "experienceB2": Second bullet point of most recent experience (if any)
   - "experienceB3": Third bullet point of most recent experience (if any)
   - "experienceB4": Fourth bullet point of most recent experience (if any)
   - "projectTitle": Most prominent project title
   - "projectLink": URL or GitHub link of the project
   - "projectB1": First bullet point of the project description
   - "projectB2": Second bullet point of the project description (if any)
   - "projectB3": Third bullet point of the project description (if any)
   - "certC1": First certification name/details
   - "certC2": Second certification name/details
   - "certC3": Third certification name/details
   - "certC4": Fourth certification name/details
2. "atsScore": An integer (0-100) representing how well the resume is optimized for ATS parsing (e.g. check for clean layout, sections, clear details, keywords).
3. "readabilityScore": An integer (0-100) representing the readability/format (font scanability, bullet lengths, etc.).
4. "industryMatchScore": An integer (0-100) representing how well-aligned the skills are with modern software/tech roles.
5. "feedback": A dictionary containing:
   - "score": Same as atsScore.
   - "missingKeywords": A list of 3-6 important technical skills/keywords that are missing or underrepresented.
   - "improvements": A list of up to 3 objects, each with {"originalText", "suggestedText", "reason"}, rewriting weak/passive phrases into XYZ formula-based achievements.
   - "mistakes": A list of formatting, phrasing, or structural mistakes found in the resume.
   - "suggestions": A list of actionable steps to fix the mistakes and improve the score.
"""

@app.post("/api/resumes/parse-guest")
async def parse_guest_resume(
    request: Request,
    file: UploadFile = File(...)
):
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF and DOCX files are allowed."
        )
        
    file_bytes = await file.read()
    if ext == ".pdf":
        text = extract_text_from_pdf_bytes(file_bytes)
    else:
        text = extract_text_from_docx_bytes(file_bytes)
        
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to extract any text from the uploaded document. Please check the file."
        )
        
    user_key = request.headers.get("X-Gemini-API-Key")
    analysis_data = None
    if user_key or os.environ.get("GEMINI_API_KEY"):
        import json
        gemini_resp = call_gemini(RESUME_PARSE_SYSTEM_PROMPT, f"Here is the raw resume text:\n{text}", user_key=user_key)
        if gemini_resp:
            try:
                cleaned = gemini_resp.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:-3]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:-3]
                analysis_data = json.loads(cleaned.strip())
            except Exception as e:
                print(f"Failed to parse gemini guest resume JSON: {e}")
                
    if not analysis_data:
        analysis_data = heuristic_parse_resume(text)
        
    return {
        "success": True,
        "filename": filename,
        "atsScore": analysis_data.get("atsScore", analysis_data.get("score", 75)),
        "readabilityScore": analysis_data.get("readabilityScore", 80),
        "industryMatchScore": analysis_data.get("industryMatchScore", 75),
        "content": analysis_data.get("content", {}),
        "feedback": analysis_data.get("feedback", {})
    }

@app.post("/api/resumes/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF and DOCX files are allowed."
        )
        
    file_bytes = await file.read()
    if ext == ".pdf":
        text = extract_text_from_pdf_bytes(file_bytes)
    else:
        text = extract_text_from_docx_bytes(file_bytes)
        
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to extract any text from the uploaded document. Please check the file."
        )
        
    user_key = request.headers.get("X-Gemini-API-Key")
    analysis_data = None
    if user_key or os.environ.get("GEMINI_API_KEY"):
        import json
        gemini_resp = call_gemini(RESUME_PARSE_SYSTEM_PROMPT, f"Here is the raw resume text:\n{text}", user_key=user_key)
        if gemini_resp:
            try:
                cleaned = gemini_resp.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:-3]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:-3]
                analysis_data = json.loads(cleaned.strip())
            except Exception as e:
                print(f"Failed to parse gemini upload resume JSON: {e}")
                
    if not analysis_data:
        analysis_data = heuristic_parse_resume(text)
        
    score = analysis_data.get("atsScore", analysis_data.get("score", 75))
    readability = analysis_data.get("readabilityScore", 80)
    match_score = analysis_data.get("industryMatchScore", 75)
    content_data = analysis_data.get("content", {})
    feedback_data = analysis_data.get("feedback", {})
    
    # Save in DB
    existing = session.exec(select(Resume).where(Resume.user_id == user.id)).first()
    if existing:
        existing.title = filename
        existing.ats_score = score
        existing.recruiter_readability_score = readability
        existing.industry_match_score = match_score
        existing.content = content_data
        existing.analysis_feedback = feedback_data
        existing.updated_at = datetime.utcnow()
        session.add(existing)
    else:
        new_res = Resume(
            id=str(uuid.uuid4()),
            user_id=user.id,
            title=filename,
            ats_score=score,
            recruiter_readability_score=readability,
            industry_match_score=match_score,
            content=content_data,
            analysis_feedback=feedback_data
        )
        session.add(new_res)
        
    session.commit()
    return {
        "success": True, 
        "filename": filename,
        "atsScore": score,
        "readabilityScore": readability,
        "industryMatchScore": match_score,
        "feedback": feedback_data
    }

# --- AI MENTOR ROUTES ---

@app.post("/api/mentor/chat")
def chat_with_mentor(
    data: MentorChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    profile = session.get(Profile, user.id)
    active_roadmap = session.exec(select(Roadmap).where(Roadmap.user_id == user.id, Roadmap.is_active == True)).first()
    
    conversation = session.exec(select(AIConversation).where(AIConversation.user_id == user.id)).first()
    if not conversation:
        conversation = AIConversation(id=str(uuid.uuid4()), user_id=user.id, title="Career Mentorship")
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

    user_msg = AIMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        sender="user",
        message=data.message
    )
    session.add(user_msg)
    session.commit()

    history_msgs = session.exec(
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation.id)
        .order_by(AIMessage.created_at.desc())
        .limit(6)
    ).all()
    history_msgs.reverse()
    
    history_str = ""
    for msg in history_msgs[:-1]:
        history_str += f"{msg.sender.capitalize()}: {msg.message}\n"

    system_prompt = f"""You are CampusMate AI, a highly experienced principal engineer and career coach.
Student Profile: Name: {profile.full_name}, Target Role: {profile.target_role or 'Not selected'}, Academic level: {profile.academic_level}.
Current active roadmap: {active_roadmap.title if active_roadmap else 'None generated yet'}.

Always:
1. Provide extremely technical, actionable, and structured markdown guidance.
2. If the user asks about system architecture, draw a clean text/ASCII block.
3. Keep the response encouraging, professional, and practical.
"""
    
    user_prompt = f"{history_str}User: {data.message}\nAssistant:"
    user_key = request.headers.get("X-Gemini-API-Key")
    response_text = call_gemini(system_prompt, user_prompt, user_key=user_key)
    
    if not response_text:
        query = data.message.lower()
        if "roadmap" in query:
            response_text = f"Hello {profile.full_name}! Regarding your roadmap for **{profile.target_role or 'your career'}**, the best next step is to master the fundamentals of Web Architectures. Start with how HTTP connections operate, then build a basic routing gateway. Focus on official Microsoft Learn resources, and try containerizing a project using Docker. Would you like me to suggest a specific project repo structure for this?"
        elif "resume" in query:
            response_text = f"I've reviewed your request. To boost your resume score, prioritize rewriting bullet points using the **Google XYZ formula**: 'Accomplished [X] as measured by [Y], by doing [Z]'. For instance, instead of saying *'Wrote python code'*, use *'Built a multi-threaded web scraper in Python, cutting data aggregation time by 40%.'*"
        elif "hackathon" in query:
            response_text = """### Hackathon Architecture Blueprint
Here is a recommended setup for building a quick, scalable MVP:

```
[HTML/CSS/Vanilla JS] --(fetch API)--> [FastAPI App (Python)] --> [SQLite DB]
                                           |
                                      (GenAI API)
                                           v
                                   [Gemini Pro LLM]
```

**Recommended Launch Strategy:**
1. Keep the landing page minimal with a striking glassmorphic design and clear call-to-actions.
2. Integrate a mock database handler first to ensure the API responses are stable.
3. Deploy directly to Railway for zero-downtime continuous updates."""
        else:
            response_text = f"That is a great question. In **{profile.target_role or 'Software Engineering'}**, we solve this by prioritizing modular development. Ensure you separate your server code from your database models, validate inputs using libraries like Pydantic, and write clean integration tests. What specific component of this stack are you currently working on?"

    assistant_msg = AIMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        sender="assistant",
        message=response_text
    )
    session.add(assistant_msg)
    session.commit()
    
    return {"reply": response_text}

# --- DASHBOARD & ANALYTICS ---

@app.get("/api/dashboard/stats")
def get_dashboard_stats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    profile = session.get(Profile, user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile details missing.")
        
    roadmap = session.exec(
        select(Roadmap).where(Roadmap.user_id == user.id, Roadmap.is_active == True)
    ).first()
    
    resume = session.exec(select(Resume).where(Resume.user_id == user.id)).first()
    
    nodes_completed = 0
    total_nodes = 0
    next_node = None
    
    if roadmap:
        nodes = session.exec(
            select(RoadmapNode).where(RoadmapNode.roadmap_id == roadmap.id)
        ).all()
        total_nodes = len(nodes)
        nodes_completed = len([n for n in nodes if n.status == "COMPLETED"])
        
        for n in nodes:
            if n.status in ["AVAILABLE", "IN_PROGRESS"]:
                next_node = n
                break
    
    return {
        "fullName": profile.full_name,
        "streak": profile.streak_count,
        "xp": profile.total_xp,
        "targetRole": profile.target_role,
        "roadmapProgress": int((nodes_completed / total_nodes * 100)) if total_nodes > 0 else 0,
        "nextNode": next_node.title if next_node else "Generate a roadmap first!",
        "resumeScore": resume.ats_score if resume else 0,
        "readabilityScore": resume.recruiter_readability_score if resume else 0,
        "industryMatchScore": resume.industry_match_score if resume else 0,
        "learningHours": 12
    }

# Mount Static Files
app.mount("/", StaticFiles(directory="static", html=True), name="static")
