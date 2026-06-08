import os
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from pydantic import BaseModel
import bcrypt
from jose import jwt, JWTError

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
    version="1.0.0"
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
SECRET_KEY = "campusmate_ai_super_secret_dev_key_change_in_production"
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
def call_gemini(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
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

    # Let's populate the nodes
    # We will trigger Gemini or a structured list fallback if no API key is set
    system_prompt = "You are a software architect that outputs roadmaps strictly in JSON format. Do not write text before or after."
    user_prompt = f"Create a learning roadmap for target role: '{data.targetRole}' with current skills: {data.skills}. Output an array of 4 sequential milestone nodes. Each node must have: 'title', 'description', 'estimated_duration', 'difficulty' ('BEGINNER', 'INTERMEDIATE', 'ADVANCED'), and list of 'resources' [{t, url}], 'projects' [{t, d, tasks}], 'certifications' [{name, provider}]."
    
    raw_response = call_gemini(system_prompt, user_prompt)
    
    nodes_data = []
    if raw_response:
        # Attempt to parse json from gemini response
        try:
            import json
            # Clean possible markdown wrap
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:-3]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:-3]
            nodes_data = json.loads(cleaned.strip())
        except Exception as e:
            print(f"Failed to parse gemini JSON roadmap: {e}")
            nodes_data = []

    # Fallback to Mock Roadmap if API is empty or parser failed
    if not nodes_data:
        # Standard mock based on targetRole
        role_lower = data.targetRole.lower()
        if "cyber" in role_lower or "security" in role_lower:
            nodes_data = [
                {
                    "title": "Networking & Security Essentials",
                    "description": "Master TCP/IP, DNS, Subnets, and firewall fundamentals.",
                    "estimated_duration": "10 hours",
                    "difficulty": "BEGINNER",
                    "resources": [{"title": "Microsoft Learn: Security Fundamentals", "url": "https://learn.microsoft.com"}],
                    "projects": [{"title": "Network Packet Analyzer", "description": "Write a python socket script to sniff and parse network packets.", "tasks": ["Setup socket listener", "Extract packet headers", "Format output log"]}],
                    "certifications": [{"name": "CompTIA Security+", "provider": "CompTIA"}]
                },
                {
                    "title": "Linux Administration & OS Security",
                    "description": "Understand Linux kernel permissions, SSH hardening, and scripting.",
                    "estimated_duration": "14 hours",
                    "difficulty": "INTERMEDIATE",
                    "resources": [{"title": "Linux Command Line Basics", "url": "https://linuxjourney.com"}],
                    "projects": [{"title": "Bash SSH Hardening Script", "description": "Create a bash script to audit and patch common SSH configurations.", "tasks": ["Disable root login", "Configure port forwarding blocking", "Auto-setup key auth"]}],
                    "certifications": [{"name": "Linux+ Certification", "provider": "CompTIA"}]
                },
                {
                    "title": "Ethical Hacking & Vulnerability Analysis",
                    "description": "Learn vulnerability scanning, Nmap, and OWASP Top 10 security threats.",
                    "estimated_duration": "20 hours",
                    "difficulty": "INTERMEDIATE",
                    "resources": [{"title": "OWASP Top 10 Security Guide", "url": "https://owasp.org"}],
                    "projects": [{"title": "Vulnerability Scanner App", "description": "Build a python tool that audits local ports and indexes vulnerabilities.", "tasks": ["Scan open ports", "Query CVE databases", "Write HTML report"]}],
                    "certifications": [{"name": "Certified Ethical Hacker (CEH)", "provider": "EC-Council"}]
                },
                {
                    "title": "Cloud Security & Azure Hardening",
                    "description": "Master identity management (IAM) and securing Azure resources.",
                    "estimated_duration": "24 hours",
                    "difficulty": "ADVANCED",
                    "resources": [{"title": "Microsoft Learn: Azure Security Center", "url": "https://learn.microsoft.com"}],
                    "projects": [{"title": "Secure Cloud Infrastructure Deployment", "description": "Deploy a secure Azure VM behind an Application Gateway with WAF.", "tasks": ["Provision Azure VNet", "Configure Network Security Groups", "Validate blocking logs"]}],
                    "certifications": [{"name": "Microsoft Certified: Azure Security Engineer Associate", "provider": "Microsoft"}]
                }
            ]
        elif "ai" in role_lower or "machine" in role_lower or "ml" in role_lower or "intelligence" in role_lower:
            nodes_data = [
                {
                    "title": "Python & Linear Algebra Fundamentals",
                    "description": "Build foundations in numpy, matrices, calculus, and basic data processing.",
                    "estimated_duration": "8 hours",
                    "difficulty": "BEGINNER",
                    "resources": [{"title": "Python Data Science Handbook", "url": "https://jakevdp.github.io/PythonDataScienceHandbook/"}],
                    "projects": [{"title": "Matrix Computation Engine", "description": "Write a pure python engine for matrix multiplication and matrix operations.", "tasks": ["Implement matrix addition", "Build multiplication loop", "Calculate determinants"]}],
                    "certifications": [{"name": "Azure AI Fundamentals (AI-900)", "provider": "Microsoft"}]
                },
                {
                    "title": "Supervised & Unsupervised Machine Learning",
                    "description": "Implement linear regression, decision trees, random forests, and KMeans using Scikit-Learn.",
                    "estimated_duration": "15 hours",
                    "difficulty": "INTERMEDIATE",
                    "resources": [{"title": "Scikit-Learn Tutorials", "url": "https://scikit-learn.org"}],
                    "projects": [{"title": "Real-Estate Price Predictor", "description": "Train a regression algorithm on local housing statistics and expose it via API.", "tasks": ["Clean missing dataset rows", "Train Random Forest Regressor", "Verify output latency"]}],
                    "certifications": [{"name": "GitHub Foundations", "provider": "GitHub"}]
                },
                {
                    "title": "Deep Learning & Neural Network Frameworks",
                    "description": "Implement simple multi-layer perceptrons and CNNs using PyTorch or TensorFlow.",
                    "estimated_duration": "22 hours",
                    "difficulty": "INTERMEDIATE",
                    "resources": [{"title": "PyTorch for Beginners Guide", "url": "https://pytorch.org"}],
                    "projects": [{"title": "Handwritten Digit Classifier", "description": "Train a Convolutional Neural Network on MNIST database and verify correctness.", "tasks": ["Prepare PyTorch DataLoader", "Train CNN model layers", "Save weights file"]}],
                    "certifications": [{"name": "Azure AI Engineer Associate (AI-102)", "provider": "Microsoft"}]
                },
                {
                    "title": "LLMs & Retrieval-Augmented Generation (RAG)",
                    "description": "Build context-aware conversational applications using LLM API vectors.",
                    "estimated_duration": "25 hours",
                    "difficulty": "ADVANCED",
                    "resources": [{"title": "LangChain Framework Tutorials", "url": "https://langchain.com"}],
                    "projects": [{"title": "DocuMind Chatbot", "description": "Build an app that answers questions from uploaded PDF folders using vector embeddings.", "tasks": ["Setup text chunk chunker", "Generate vector embeddings", "Query Gemini LLM"]}],
                    "certifications": [{"name": "Microsoft Certified: Azure Data Scientist Associate", "provider": "Microsoft"}]
                }
            ]
        else:
            # Default Web / Software Engineering mock
            nodes_data = [
                {
                    "title": "HTML5, CSS3, and JavaScript Basics",
                    "description": "Learn semantic document design, CSS custom selectors, flex layouts, and ES6 scripting.",
                    "estimated_duration": "10 hours",
                    "difficulty": "BEGINNER",
                    "resources": [{"title": "MDN Web Docs: Learn Web Development", "url": "https://developer.mozilla.org"}],
                    "projects": [{"title": "Interactive SaaS Dashboard mockup", "description": "Design a responsive frontend screen using custom CSS variables.", "tasks": ["Configure layout layout grid", "Implement glassmorphic styling", "Add dark mode toggler"]}],
                    "certifications": [{"name": "FreeCodeCamp Frontend Developer Certification", "provider": "FreeCodeCamp"}]
                },
                {
                    "title": "Backend Web Servers & API Design",
                    "description": "Configure HTTP backend routes, middleware handlers, and JSON request validation.",
                    "estimated_duration": "15 hours",
                    "difficulty": "INTERMEDIATE",
                    "resources": [{"title": "FastAPI Web Tutorials", "url": "https://fastapi.tiangolo.com"}],
                    "projects": [{"title": "Dockerized Book Registry API", "description": "Create a FastAPI backend with persistent SQLite container mappings.", "tasks": ["Setup FastAPI controllers", "Define SQLAlchemy tables", "Create Dockerfile wrapper"]}],
                    "certifications": [{"name": "GitHub Foundations Certification", "provider": "GitHub"}]
                },
                {
                    "title": "Database Optimization & Indexing",
                    "description": "Learn SQL relationships, indexing strategies, connections pooling, and ACID features.",
                    "estimated_duration": "18 hours",
                    "difficulty": "INTERMEDIATE",
                    "resources": [{"title": "PostgreSQL Tutorials", "url": "https://postgresqltutorial.com"}],
                    "projects": [{"title": "Performance Tuning Sandbox", "description": "Seed database with 100k rows and run queries, analyzing latency metrics.", "tasks": ["Generate test seed data", "Measure unindexed vs indexed timing", "Configure Connection Pools"]}],
                    "certifications": [{"name": "Microsoft Certified: Azure Database Administrator", "provider": "Microsoft"}]
                },
                {
                    "title": "CI/CD Automations & Cloud Container Deployments",
                    "description": "Setup automated verification steps, Docker registries, and configure auto-releasing pipelines.",
                    "estimated_duration": "22 hours",
                    "difficulty": "ADVANCED",
                    "resources": [{"title": "GitHub Actions Docs", "url": "https://docs.github.com"}],
                    "projects": [{"title": "Automated Pipeline Project", "description": "Write a workflow that compiles code, runs test suites, and deploys on Railway.", "tasks": ["Write GitHub actions yaml file", "Pass linter checks", "Configure Docker registry auth"]}],
                    "certifications": [{"name": "Microsoft Certified: DevOps Engineer Expert", "provider": "Microsoft"}]
                }
            ]

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
        parent_id = node_id # next node parent is current node
    
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
    
    # Sort nodes by dependency hierarchy manually
    sorted_nodes = []
    nodes_by_parent = {n.parent_node_id: n for n in nodes}
    
    curr_parent = None
    # Follow chain starting from parent_node_id == None
    for _ in range(len(nodes)):
        if curr_parent in nodes_by_parent:
            n = nodes_by_parent[curr_parent]
            sorted_nodes.append(n)
            curr_parent = n.id
        else:
            break
            
    # Add any remaining nodes that didn't sort cleanly (fallback)
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
    
    # If node is completed, unlock the immediate child node
    if data.status == "COMPLETED":
        # Gain XP
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
    # Find existing or create new
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
    user_prompt = f"Analyze this resume JSON: {resume.content} against target job description: '{data.targetJobDescription}'. Return a JSON with: 'score' (0-100), 'missingKeywords' (list of missing skills), 'improvements' (list of {{'originalText', 'suggestedText', 'reason'}})."
    
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
        # High quality offline mock analysis fallback
        # Inspect target job to customize mock keywords
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
            ]
        }

    resume.ats_score = analysis_data.get("score", 70)
    resume.analysis_feedback = analysis_data
    resume.updated_at = datetime.utcnow()
    
    # Award XP on first analysis
    profile = session.get(Profile, user.id)
    if profile:
        profile.total_xp += 50
        session.add(profile)
        
    session.add(resume)
    session.commit()
    session.refresh(resume)
    
    return {"success": True, "resume": resume}

# --- AI MENTOR ROUTES ---

@app.post("/api/mentor/chat")
def chat_with_mentor(
    data: MentorChatRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    profile = session.get(Profile, user.id)
    active_roadmap = session.exec(select(Roadmap).where(Roadmap.user_id == user.id, Roadmap.is_active == True)).first()
    
    # Retrieve recent chat history (last 5 messages) to maintain context
    conversation = session.exec(select(AIConversation).where(AIConversation.user_id == user.id)).first()
    if not conversation:
        conversation = AIConversation(id=str(uuid.uuid4()), user_id=user.id, title="Career Mentorship")
        session.add(conversation)
        session.commit()
        session.refresh(conversation)

    # Save user message
    user_msg = AIMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        sender="user",
        message=data.message
    )
    session.add(user_msg)
    session.commit()

    # Get history
    history_msgs = session.exec(
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation.id)
        .order_by(AIMessage.created_at.desc())
        .limit(6)
    ).all()
    history_msgs.reverse() # Sort in ascending order (older first)
    
    history_str = ""
    for msg in history_msgs[:-1]: # exclude the current user message which is already processed
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
    
    response_text = call_gemini(system_prompt, user_prompt)
    
    if not response_text:
        # High quality mock response logic (inspects message contents)
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

    # Save assistant message
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
        
        # Find next node (first available or in progress node)
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
        "learningHours": 12 # Mock hours tracking for display widgets
    }

# Mount Static Files (Must be mounted at the end to prevent overriding API paths)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
