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
from app.models import db, User, ChatMessage, ResumeAnalysis, RoadmapProgress
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
            ("Capstone: Deploy Secure Cloud Cluster", "Deploy a complete SaaS network behind load balancers with WAF."),
            ("Capstone High-Availability Architecture", "Present solutions blueprint achieving 99.99% multi-region uptime.")
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
            ("Capstone: Zero-Downtime CD Pipeline", "Deliver an automated pipeline that builds, tests, and rolls updates."),
            ("Capstone System Resilience Verification", "Conduct chaos experiments testing server pool auto-recovery.")
        ]
        provider = "HashiCorp / RedHat"
        cert = "HashiCorp Certified: Terraform Associate"
    # 7. Full Stack Web Development
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
            ("Capstone: Deploy E-Commerce Platform", "Deploy a complete app containing user auth, items, and billing."),
            ("Capstone Deployment Validation", "Execute cypress visual validation tests verifying dynamic cart state.")
        ]
        provider = "FreeCodeCamp / OpenJS"
        cert = "Meta Front-End Developer Certificate"
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
            "id": f"node-{i+1}",
            "title": f"Step {i+1}: {title}",
            "description": desc,
            "difficulty": diff,
            "estimated_duration": dur,
            "resources": [{"title": f"Official documentation for {title}", "url": "https://docs.microsoft.com"}],
            "projects": [{"title": f"Implementation Project - Step {i+1}", "description": f"Build a practical system that demonstrates deep knowledge of {title}.", "tasks": ["Configure the framework settings", "Write code files implementation", "Verify local test suits passes"]}],
            "certifications": [{"name": cert, "provider": provider}]
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
        "Cyber Security", 
        "AI Engineering", 
        "Machine Learning", 
        "Data Science", 
        "Cloud Computing", 
        "DevOps", 
        "Full Stack Web Development", 
        "Mobile Development"
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
        "total_count": len(nodes)
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
    text_paste = request.form.get('resume_text', '').strip()
    target_role = request.form.get('target_role', 'Software Engineer')
    
    extracted_text = ""
    filename = "Pasted_Resume_Text"
    
    if file and file.filename != '':
        filename = file.filename
        file_bytes = file.read()
        if filename.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_bytes)
        elif filename.lower().endswith('.docx'):
            extracted_text = extract_text_from_docx(file_bytes)
        else:
            flash("Unsupported file extension. Only PDF and DOCX are allowed.", "danger")
            return redirect(url_for('features.resume_analyzer'))
    elif text_paste:
        extracted_text = text_paste
    else:
        flash("Please upload a file or paste your resume text.", "danger")
        return redirect(url_for('features.resume_analyzer'))
        
    if not extracted_text:
        flash("Could not extract any readable text from the file.", "danger")
        return redirect(url_for('features.resume_analyzer'))
        
    analysis = heuristic_parse_resume(extracted_text)
    analysis['target_role'] = target_role
    
    new_analysis = ResumeAnalysis(
        user_id=current_user.id,
        filename=filename,
        ats_score=analysis['atsScore'],
        readability_score=analysis['readabilityScore'],
        industry_match_score=analysis['industryMatchScore'],
        target_role=target_role,
        analysis_json=json.dumps(analysis)
    )
    db.session.add(new_analysis)
    db.session.commit()
    
    flash("Resume analyzed successfully!", "success")
    return redirect(url_for('features.resume_analyzer'))

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
