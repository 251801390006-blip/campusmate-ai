// CampusMate AI Client Router & Controller
let appMode = "server"; // "server" or "sandbox"
let currentUser = null;
let activeRoadmap = null;
let activeNodes = [];
let mockInterviewState = {
    active: false,
    role: "",
    questionIndex: 0,
    questions: [
        "What is the difference between TCP and UDP, and in what scenarios would you choose one over the other?",
        "Explain how a SQL Injection occurs and detail two distinct prevention strategies on the application layer.",
        "How do index tables optimize search latency, and what is the trade-off of maintaining too many indices?"
    ],
    answers: []
};

// Start initialization on DOM content load
document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    // Check if there is a saved sandbox session
    if (localStorage.getItem("campusmate_sandbox_active") === "true") {
        launchSandboxMode();
        return;
    }

    if (API.isLoggedIn()) {
        try {
            appMode = "server";
            currentUser = await API.getMe();
            showMainApp();
            loadDashboard();
        } catch (e) {
            console.error("Server connection failed, checking offline availability...", e);
            handleLogout();
        }
    }
}

// --- CORE LAYOUT TOGGLERS ---
function showAuthModal(tab) {
    document.getElementById("auth-overlay").classList.remove("hidden");
    switchAuthTab(tab);
}

function closeAuthModal() {
    document.getElementById("auth-overlay").classList.add("hidden");
}

function switchAuthTab(tab) {
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");
    const loginTabBtn = document.getElementById("tab-login-btn");
    const signupTabBtn = document.getElementById("tab-signup-btn");
    const errorMsg = document.getElementById("auth-error-msg");

    errorMsg.classList.add("hidden");

    if (tab === "login") {
        loginForm.classList.remove("hidden");
        signupForm.classList.add("hidden");
        loginTabBtn.classList.add("active");
        signupTabBtn.classList.remove("active");
    } else {
        loginForm.classList.add("hidden");
        signupForm.classList.remove("hidden");
        loginTabBtn.classList.remove("active");
        signupTabBtn.classList.add("active");
    }
}

// --- SANDBOX MODE LAUNCHER ---
function launchSandboxMode() {
    appMode = "sandbox";
    localStorage.setItem("campusmate_sandbox_active", "true");
    
    // Create guest user profile if not present
    let sandboxUser = localStorage.getItem("campusmate_sandbox_user");
    if (!sandboxUser) {
        currentUser = {
            id: "guest-student",
            fullName: "Guest Student",
            academicLevel: "UNDERGRADUATE",
            institution: "Sandbox University",
            targetRole: "Full-Stack Dev",
            streak: 3,
            xp: 350
        };
        localStorage.setItem("campusmate_sandbox_user", JSON.stringify(currentUser));
        
        // Seed default sandbox roadmap
        seedSandboxRoadmap("Full-Stack Dev");
    } else {
        currentUser = JSON.parse(sandboxUser);
    }
    
    // Show sandbox UI indicators
    document.getElementById("sandbox-badge").classList.remove("hidden");
    
    // Transition layouts
    document.getElementById("landing-container").classList.add("hidden");
    closeAuthModal();
    showMainApp();
    loadDashboard();
}

function seedSandboxRoadmap(role) {
    const nodes = [
        {
            id: "node-1",
            title: "HTML5, CSS3, and JavaScript Basics",
            description: "Learn semantic document design, CSS custom selectors, and ES6 scripting.",
            difficulty: "BEGINNER",
            estimated_duration: "10 hours",
            resources: [{title: "MDN Web Docs: Learn Web Development", url: "https://developer.mozilla.org"}],
            projects: [{title: "Interactive SaaS Dashboard", description: "Design a responsive frontend screen using custom CSS variables.", tasks: ["Configure layout grid", "Implement glassmorphic styling", "Add dark mode toggler"]}],
            certifications: [{name: "FreeCodeCamp Frontend Developer Certification", provider: "FreeCodeCamp"}],
            status: "AVAILABLE"
        },
        {
            id: "node-2",
            title: "Backend Web Servers & API Design",
            description: "Configure HTTP backend routes, middleware handlers, and JSON request validation.",
            difficulty: "INTERMEDIATE",
            estimated_duration: "15 hours",
            resources: [{title: "FastAPI Web Tutorials", url: "https://fastapi.tiangolo.com"}],
            projects: [{title: "Dockerized Book Registry API", description: "Create a FastAPI backend with persistent SQLite container mappings.", tasks: ["Setup FastAPI controllers", "Define SQLAlchemy tables", "Create Dockerfile wrapper"]}],
            certifications: [{name: "GitHub Foundations", provider: "GitHub"}],
            status: "LOCKED"
        },
        {
            id: "node-3",
            title: "Database Optimization & Indexing",
            description: "Learn SQL relationships, indexing strategies, connections pooling, and ACID features.",
            difficulty: "INTERMEDIATE",
            estimated_duration: "18 hours",
            resources: [{title: "PostgreSQL Tutorials", url: "https://postgresqltutorial.com"}],
            projects: [{"title": "Performance Tuning Sandbox", "description": "Seed database with 100k rows and run queries, analyzing latency metrics.", "tasks": ["Generate test seed data", "Measure unindexed vs indexed timing", "Configure Connection Pools"]}],
            certifications: [{name: "Microsoft Certified: Database Administrator", provider: "Microsoft"}],
            status: "LOCKED"
        },
        {
            id: "node-4",
            title: "CI/CD Automations & Cloud Container Deployments",
            description: "Setup automated verification steps, Docker registries, and configure auto-releasing pipelines.",
            difficulty: "ADVANCED",
            estimated_duration: "22 hours",
            resources: [{title: "GitHub Actions Docs", url: "https://docs.github.com"}],
            projects: [{"title": "Automated Pipeline Project", "description": "Write a workflow that compiles code, runs test suites, and deploys on Railway.", "tasks": ["Write GitHub actions yaml file", "Pass linter checks", "Configure Docker registry auth"]}],
            certifications: [{name: "Microsoft Certified: DevOps Engineer Expert", provider: "Microsoft"}],
            status: "LOCKED"
        }
    ];
    
    localStorage.setItem("campusmate_sandbox_roadmap", JSON.stringify({
        title: `${role} Dynamic Pathway (Sandbox)`,
        targetRole: role
    }));
    localStorage.setItem("campusmate_sandbox_nodes", JSON.stringify(nodes));
}

// --- AUTH HANDLERS ---
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    const errorMsg = document.getElementById("auth-error-msg");

    try {
        appMode = "server";
        await API.login(email, password);
        currentUser = await API.getMe();
        
        document.getElementById("sandbox-badge").classList.add("hidden");
        document.getElementById("landing-container").classList.add("hidden");
        closeAuthModal();
        showMainApp();
        loadDashboard();
    } catch (error) {
        console.error(error);
        errorMsg.innerText = "Connection failed. Please verify uvicorn is running on local port 8000, or switch to Sandbox Mode.";
        errorMsg.classList.remove("hidden");
    }
}

async function handleSignup(e) {
    e.preventDefault();
    const fullName = document.getElementById("signup-name").value;
    const email = document.getElementById("signup-email").value;
    const password = document.getElementById("signup-password").value;
    const academicLevel = document.getElementById("signup-level").value;
    const errorMsg = document.getElementById("auth-error-msg");

    try {
        appMode = "server";
        await API.register(email, password, fullName, academicLevel);
        currentUser = await API.getMe();
        
        document.getElementById("sandbox-badge").classList.add("hidden");
        document.getElementById("landing-container").classList.add("hidden");
        closeAuthModal();
        showMainApp();
        loadDashboard();
    } catch (error) {
        console.error(error);
        errorMsg.innerText = "Connection failed. Try local Sandbox Mode if server is offline.";
        errorMsg.classList.remove("hidden");
    }
}

function handleLogout() {
    API.clearToken();
    localStorage.removeItem("campusmate_sandbox_active");
    currentUser = null;
    activeRoadmap = null;
    activeNodes = [];
    
    // Hide sandbox UI badges
    document.getElementById("sandbox-badge").classList.add("hidden");
    
    // Restore landing page views
    document.getElementById("landing-container").classList.remove("hidden");
    document.getElementById("app-container").classList.add("hidden");
}

function showMainApp() {
    document.getElementById("app-container").classList.remove("hidden");
    
    // Update profile sidebar badges
    document.getElementById("user-display-name").innerText = currentUser.fullName;
    document.getElementById("user-display-level").innerText = currentUser.academicLevel.replace("_", " ");
    document.getElementById("avatar-initials").innerText = currentUser.fullName.split(" ").map(n => n[0]).join("").toUpperCase();
    
    // Update top header status
    document.getElementById("streak-counter").innerText = currentUser.streak || 1;
    document.getElementById("xp-counter").innerText = currentUser.xp || 100;
}

// --- VIEW ROUTER ---
function navigateToTab(tabName) {
    document.querySelectorAll(".menu-item").forEach(item => {
        if (item.getAttribute("data-tab") === tabName) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    const titleEl = document.getElementById("tab-title");
    const subEl = document.getElementById("tab-subtitle");
    
    if (tabName === "dashboard") {
        titleEl.innerText = "Student Growth Dashboard";
        subEl.innerText = "Track your goals, streaks, and target roadmaps.";
        loadDashboard();
    } else if (tabName === "roadmap") {
        titleEl.innerText = "Roadmap Engine";
        subEl.innerText = "Generate and follow visual non-linear learning roadmaps.";
        loadRoadmapView();
    } else if (tabName === "resume") {
        titleEl.innerText = "ATS Resume Builder";
        subEl.innerText = "Build, analyze, and optimize your resume for applicant tracking filters.";
        loadResumeView();
    } else if (tabName === "mock") {
        titleEl.innerText = "Interview Simulator";
        subEl.innerText = "Practice technical interview questions with your AI Mentor.";
        loadMockInterviewView();
    } else if (tabName === "hackathon") {
        titleEl.innerText = "Hackathon Assistant";
        subEl.innerText = "Form concepts, structural architectures, and pitch presentations.";
        loadHackathonView();
    }

    document.querySelectorAll(".tab-view").forEach(view => {
        if (view.id === `view-${tabName}`) {
            view.classList.remove("hidden-view");
            view.classList.add("active-view");
        } else {
            view.classList.add("hidden-view");
            view.classList.remove("active-view");
        }
    });
}

// --- LOAD DASHBOARD DETAILS ---
async function loadDashboard() {
    try {
        let stats = {};
        
        if (appMode === "sandbox") {
            // Load from sandbox localstorage
            const roadmapInfo = JSON.parse(localStorage.getItem("campusmate_sandbox_roadmap") || "null");
            const nodes = JSON.parse(localStorage.getItem("campusmate_sandbox_nodes") || "[]");
            const resumeScore = localStorage.getItem("campusmate_sandbox_resumescore") || 0;
            
            const completedCount = nodes.filter(n => n.status === "COMPLETED").length;
            const progress = nodes.length > 0 ? Math.round((completedCount / nodes.length) * 100) : 0;
            const nextNode = nodes.find(n => n.status === "AVAILABLE" || n.status === "IN_PROGRESS");
            
            stats = {
                fullName: currentUser.fullName,
                streak: currentUser.streak,
                xp: currentUser.xp,
                targetRole: roadmapInfo ? roadmapInfo.targetRole : null,
                roadmapProgress: progress,
                nextNode: nextNode ? nextNode.title : "Generate a roadmap first!",
                resumeScore: parseInt(resumeScore),
                learningHours: 14
            };
        } else {
            stats = await API.getDashboardStats();
        }

        // Render widgets
        document.getElementById("dashboard-target-role").innerText = stats.targetRole || "Not Configured";
        document.getElementById("dashboard-roadmap-progress").style.width = `${stats.roadmapProgress}%`;
        document.getElementById("dashboard-roadmap-progress-text").innerText = `${stats.roadmapProgress}% Completed`;
        document.getElementById("dashboard-resume-score").innerText = `${stats.resumeScore} / 100`;

        document.getElementById("streak-counter").innerText = stats.streak;
        document.getElementById("xp-counter").innerText = stats.xp;
        
        const nextTaskBody = document.getElementById("dashboard-next-task-body");
        if (stats.targetRole) {
            nextTaskBody.innerHTML = `
                <div class="next-task-box">
                    <h4>Current Goal Target: <strong>${stats.nextNode}</strong></h4>
                    <p class="stat-meta">Next upcoming checkpoint in your target career roadmap.</p>
                    <button class="btn btn-sm btn-cyan mt-10" onclick="navigateToTab('roadmap')">Resume Learning <i class="fa-solid fa-arrow-right"></i></button>
                </div>
            `;
        } else {
            nextTaskBody.innerHTML = `<p class="empty-state">No roadmap initialized yet. Select your goal in the Roadmap Engine to begin!</p>`;
        }
    } catch (e) {
        console.error("Dashboard loading failed", e);
    }
}

// --- ROADMAP ENGINE FUNCTIONS ---
async function loadRoadmapView() {
    const setupOverlay = document.getElementById("roadmap-setup");
    const activeLayout = document.getElementById("roadmap-active-container");
    const treeCanvas = document.getElementById("roadmap-tree-canvas");

    treeCanvas.innerHTML = `<p class="empty-state">Loading learning pathway...</p>`;

    try {
        if (appMode === "sandbox") {
            const roadmapInfo = JSON.parse(localStorage.getItem("campusmate_sandbox_roadmap") || "null");
            activeNodes = JSON.parse(localStorage.getItem("campusmate_sandbox_nodes") || "[]");
            activeRoadmap = roadmapInfo;
        } else {
            const res = await API.getActiveRoadmap();
            activeRoadmap = res.roadmap;
            activeNodes = res.nodes;
        }

        if (activeRoadmap) {
            setupOverlay.classList.add("hidden");
            activeLayout.classList.remove("hidden");
            document.getElementById("active-roadmap-title").innerText = activeRoadmap.title;
            renderRoadmapTree();
        } else {
            setupOverlay.classList.remove("hidden");
            activeLayout.classList.add("hidden");
        }
    } catch (e) {
        console.error(e);
    }
}

async function triggerRoadmapGeneration() {
    const career = document.getElementById("target-career-input").value.trim();
    const skillsText = document.getElementById("current-skills-input").value.trim();
    
    if (!career) {
        alert("Please enter a target job role.");
        return;
    }

    const skills = skillsText ? skillsText.split(",").map(s => s.trim()) : [];
    const treeCanvas = document.getElementById("roadmap-tree-canvas");
    treeCanvas.innerHTML = `<div class="empty-state"><i class="fa-solid fa-spinner fa-spin fa-2xl mb-10"></i><p>Deep reasoning AI engine formulating roadmap milestones...</p></div>`;
    
    document.getElementById("roadmap-setup").classList.add("hidden");
    document.getElementById("roadmap-active-container").classList.remove("hidden");

    try {
        if (appMode === "sandbox") {
            // Seed locally
            seedSandboxRoadmap(career);
            currentUser.targetRole = career;
            localStorage.setItem("campusmate_sandbox_user", JSON.stringify(currentUser));
            
            // Artificial delay to make it feel premium
            setTimeout(() => {
                loadRoadmapView();
            }, 1000);
        } else {
            await API.generateRoadmap(career, skills);
            loadRoadmapView();
        }
    } catch (e) {
        alert("Failed to generate roadmap: " + e.message);
        resetRoadmapSetup();
    }
}

function resetRoadmapSetup() {
    if (appMode === "sandbox") {
        localStorage.removeItem("campusmate_sandbox_roadmap");
        localStorage.removeItem("campusmate_sandbox_nodes");
        currentUser.targetRole = null;
        localStorage.setItem("campusmate_sandbox_user", JSON.stringify(currentUser));
        loadRoadmapView();
    } else {
        resetRoadmapSetupOnServer();
    }
}

async function resetRoadmapSetupOnServer() {
    try {
        // Just trigger standard setup display
        document.getElementById("roadmap-setup").classList.remove("hidden");
        document.getElementById("roadmap-active-container").classList.add("hidden");
    } catch(e){}
}

function renderRoadmapTree() {
    const canvas = document.getElementById("roadmap-tree-canvas");
    canvas.innerHTML = "";

    if (activeNodes.length === 0) {
        canvas.innerHTML = `<p class="empty-state">No nodes generated.</p>`;
        return;
    }

    activeNodes.forEach((node, index) => {
        const div = document.createElement("div");
        div.className = `glass-card roadmap-node-badge ${node.status}`;
        
        let statusIcon = "lock";
        if (node.status === "COMPLETED") statusIcon = "check";
        else if (node.status === "IN_PROGRESS") statusIcon = "spinner fa-spin";
        else if (node.status === "AVAILABLE") statusIcon = "circle-play";

        div.innerHTML = `
            <div class="node-status-indicator"><i class="fa-solid fa-${statusIcon}"></i></div>
            <div class="node-content-details">
                <h4>${node.title}</h4>
                <p>${node.description}</p>
            </div>
        `;
        
        if (node.status !== "LOCKED") {
            div.onclick = () => openNodeModal(node);
        }
        
        canvas.appendChild(div);
    });
}

let selectedNode = null;
function openNodeModal(node) {
    selectedNode = node;
    document.getElementById("node-modal-title").innerText = node.title;
    document.getElementById("node-modal-desc").innerText = node.description;
    document.getElementById("node-modal-difficulty").innerText = node.difficulty;
    document.getElementById("node-modal-duration").innerText = node.estimated_duration;

    const resList = document.getElementById("node-modal-resources");
    resList.innerHTML = "";
    if (node.resources && node.resources.length > 0) {
        node.resources.forEach(r => {
            resList.innerHTML += `<li><i class="fa-solid fa-arrow-up-right-from-square"></i> <a href="${r.url}" target="_blank">${r.title}</a></li>`;
        });
    } else {
        resList.innerHTML = "<li>No specific resources listed. Search Microsoft Learn.</li>";
    }

    const projBox = document.getElementById("node-modal-project");
    projBox.innerHTML = "";
    if (node.projects && node.projects.length > 0) {
        const p = node.projects[0];
        projBox.innerHTML = `
            <strong>${p.title}</strong>
            <p style="margin: 8px 0; color: #94a3b8;">${p.description}</p>
            <ul style="margin-left: 15px;">
                ${p.tasks.map(t => `<li>${t}</li>`).join("")}
            </ul>
        `;
    } else {
        projBox.innerHTML = "No mini-project mapped to this node.";
    }

    const certList = document.getElementById("node-modal-certs");
    certList.innerHTML = "";
    if (node.certifications && node.certifications.length > 0) {
        node.certifications.forEach(c => {
            certList.innerHTML += `<li><i class="fa-solid fa-certificate"></i> ${c.name} (by ${c.provider})</li>`;
        });
    } else {
        certList.innerHTML = "<li>No matched cert mapping.</li>";
    }

    const actionBtn = document.getElementById("node-modal-action-btn");
    if (node.status === "COMPLETED") {
        actionBtn.innerText = "Completed!";
        actionBtn.disabled = true;
        actionBtn.className = "btn btn-outline";
    } else {
        actionBtn.innerHTML = `Mark Complete <i class="fa-solid fa-check"></i>`;
        actionBtn.disabled = false;
        actionBtn.className = "btn btn-primary";
    }

    document.getElementById("node-modal").classList.remove("hidden");
}

function closeNodeModal() {
    document.getElementById("node-modal").classList.add("hidden");
    selectedNode = null;
}

async function markNodeAsCompleted() {
    if (!selectedNode) return;
    try {
        if (appMode === "sandbox") {
            // Update locally
            const nodes = JSON.parse(localStorage.getItem("campusmate_sandbox_nodes"));
            const idx = nodes.findIndex(n => n.id === selectedNode.id);
            if (idx !== -1) {
                nodes[idx].status = "COMPLETED";
                
                // Unlock next node
                if (idx + 1 < nodes.length) {
                    nodes[idx + 1].status = "AVAILABLE";
                }
            }
            localStorage.setItem("campusmate_sandbox_nodes", JSON.stringify(nodes));
            
            // Add XP
            currentUser.xp += 100;
            localStorage.setItem("campusmate_sandbox_user", JSON.stringify(currentUser));
            
            closeNodeModal();
            loadRoadmapView();
        } else {
            await API.updateNodeStatus(selectedNode.id, "COMPLETED");
            closeNodeModal();
            loadRoadmapView();
        }
    } catch (e) {
        alert("Failed to complete node: " + e.message);
    }
}

// --- RESUME BUILDER FUNCTIONS ---
async function loadResumeView() {
    try {
        let resume = null;
        if (appMode === "sandbox") {
            resume = JSON.parse(localStorage.getItem("campusmate_sandbox_resume") || "null");
        } else {
            const res = await API.getResumes();
            if (res.resumes && res.resumes.length > 0) {
                resume = res.resumes[0];
            }
        }

        if (resume) {
            document.getElementById("resume-title-field").value = resume.title;
            document.getElementById("resume-theme-select").value = resume.theme;
            
            const c = resume.content;
            document.getElementById("res-name").value = c.name || "";
            document.getElementById("res-email").value = c.email || "";
            document.getElementById("res-phone").value = c.phone || "";
            document.getElementById("res-github").value = c.github || "";
            document.getElementById("res-exp-role").value = c.experienceRole || "";
            document.getElementById("res-exp-desc").value = c.experienceDesc || "";
            document.getElementById("res-proj-title").value = c.projectTitle || "";
            document.getElementById("res-proj-desc").value = c.projectDesc || "";
            
            changeResumeTheme();
            syncResumeFields();
            
            if (resume.analysis_feedback) {
                renderATSFeedback(resume.analysis_feedback);
            }
        }
    } catch (e) {
        console.error("Failed to load resume", e);
    }
}

function syncResumeFields() {
    document.getElementById("res-render-name").innerText = document.getElementById("res-name").value;
    document.getElementById("res-render-email").innerText = document.getElementById("res-email").value;
    document.getElementById("res-render-phone").innerText = document.getElementById("res-phone").value;
    document.getElementById("res-render-links").innerText = document.getElementById("res-github").value;
    document.getElementById("res-render-exp-title").innerText = document.getElementById("res-exp-role").value;
    document.getElementById("res-render-exp-desc").innerText = document.getElementById("res-exp-desc").value;
    document.getElementById("res-render-proj-title").innerText = document.getElementById("res-proj-title").value;
    document.getElementById("res-render-proj-desc").innerText = document.getElementById("res-proj-desc").value;
}

document.querySelectorAll(".resume-fields-panel input, .resume-fields-panel textarea").forEach(el => {
    el.addEventListener("input", syncResumeFields);
});

function changeResumeTheme() {
    const theme = document.getElementById("resume-theme-select").value;
    const paper = document.getElementById("resume-sheet-paper");
    paper.className = `resume-sheet ${theme}`;
}

async function saveResumeContent() {
    const title = document.getElementById("resume-title-field").value;
    const theme = document.getElementById("resume-theme-select").value;
    
    const content = {
        name: document.getElementById("res-name").value,
        email: document.getElementById("res-email").value,
        phone: document.getElementById("res-phone").value,
        github: document.getElementById("res-github").value,
        experienceRole: document.getElementById("res-exp-role").value,
        experienceDesc: document.getElementById("res-exp-desc").value,
        projectTitle: document.getElementById("res-proj-title").value,
        projectDesc: document.getElementById("res-proj-desc").value
    };

    try {
        if (appMode === "sandbox") {
            const resumeObj = {
                title,
                theme,
                content,
                analysis_feedback: JSON.parse(localStorage.getItem("campusmate_sandbox_resume_feedback") || "null")
            };
            localStorage.setItem("campusmate_sandbox_resume", JSON.stringify(resumeObj));
            alert("Sandbox resume draft saved locally!");
        } else {
            await API.saveResume(title, theme, content);
            alert("Resume draft saved successfully!");
        }
    } catch (e) {
        alert("Failed to save resume: " + e.message);
    }
}

async function triggerResumeATSAnalysis() {
    const targetRole = currentUser.targetRole;
    if (!targetRole) {
        alert("Please configure a target role in the Roadmap tab first.");
        return;
    }
    
    const atsBox = document.getElementById("ats-analysis-body");
    atsBox.innerHTML = `<div class="empty-state"><i class="fa-solid fa-spinner fa-spin fa-lg mr-8"></i> Running AI checks...</div>`;

    try {
        if (appMode === "sandbox") {
            // Dynamic mock score based on text inputs
            const exp = document.getElementById("res-exp-desc").value.toLowerCase();
            const proj = document.getElementById("res-proj-desc").value.toLowerCase();
            
            let score = 55;
            let missing = ["Docker", "PostgreSQL Indexes", "Connection Pools", "RESTful APIs"];
            
            // Reward inclusion of active verbs or tech keywords
            if (exp.includes("architected") || exp.includes("optimized")) score += 15;
            if (proj.includes("docker") || proj.includes("api")) score += 10;
            if (proj.includes("postgresql") || proj.includes("sqlite")) score += 10;
            
            const feedback = {
                score: Math.min(score, 100),
                missingKeywords: missing,
                improvements: [
                    {
                        originalText: "Responsible for coding the backend of the student project application.",
                        suggestedText: "Architected backend API routing structures in FastAPI, reducing request controller latency by 20%.",
                        reason: "Vague phrasing. Replace with action verbs and metrics."
                    },
                    {
                        originalText: "Wrote backend scripts to parse directories.",
                        suggestedText: "Developed asynchronous filesystem parser utilities in Python, optimizing directory traversal speed by 40%.",
                        reason: "Replaced flat description with exact technical stack and performance metrics."
                    }
                ]
            };
            
            localStorage.setItem("campusmate_sandbox_resumescore", feedback.score);
            localStorage.setItem("campusmate_sandbox_resume_feedback", JSON.stringify(feedback));
            
            // Sync with current loaded resume object
            const resumeObj = JSON.parse(localStorage.getItem("campusmate_sandbox_resume") || "{}");
            resumeObj.analysis_feedback = feedback;
            localStorage.setItem("campusmate_sandbox_resume", JSON.stringify(resumeObj));
            
            // Award XP
            currentUser.xp += 50;
            localStorage.setItem("campusmate_sandbox_user", JSON.stringify(currentUser));
            
            setTimeout(() => {
                renderATSFeedback(feedback);
                document.getElementById("dashboard-resume-score").innerText = `${feedback.score} / 100`;
            }, 1000);
        } else {
            const res = await API.analyzeResume(targetRole);
            renderATSFeedback(res.resume.analysis_feedback);
            document.getElementById("dashboard-resume-score").innerText = `${res.resume.ats_score} / 100`;
        }
    } catch (e) {
        alert("Failed to analyze resume: " + e.message);
        atsBox.innerHTML = `<p class="error-msg">Analysis failed. Check connection.</p>`;
    }
}

function renderATSFeedback(feedback) {
    document.getElementById("ats-score-display").innerText = `${feedback.score}%`;
    
    const body = document.getElementById("ats-analysis-body");
    body.innerHTML = `
        <div class="ats-recs">
            <div>
                <strong>Missing Keywords:</strong>
                <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:6px;">
                    ${feedback.missingKeywords.map(k => `<span class="header-stat-badge" style="padding:4px 8px; font-size:11px;">${k}</span>`).join("")}
                </div>
            </div>
            <hr class="divider" style="margin:10px 0;">
            <strong>Suggested Rewrites:</strong>
            ${feedback.improvements.map(i => `
                <div class="rec-item">
                    <p style="color:var(--text-secondary); text-decoration:line-through; font-size:12px;">"${i.originalText}"</p>
                    <p style="color:var(--cyan); margin:4px 0; font-weight:500;">"${i.suggestedText}"</p>
                    <p class="stat-meta" style="font-size:11px;">Reason: ${i.reason}</p>
                </div>
            `).join("")}
        </div>
    `;
}

// --- AI MENTOR DRAWER CONTROL ---
function toggleMentorDrawer() {
    const drawer = document.getElementById("mentor-drawer");
    const arrow = document.getElementById("mentor-arrow-icon");
    drawer.classList.toggle("active");
    
    if (drawer.classList.contains("active")) {
        arrow.className = "fa-solid fa-chevron-down";
    } else {
        arrow.className = "fa-solid fa-chevron-up";
    }
}

async function sendMentorMessage(e) {
    e.preventDefault();
    const input = document.getElementById("mentor-user-input");
    const msg = input.value.trim();
    if (!msg) return;

    input.value = "";
    const messagesBox = document.getElementById("mentor-chat-messages");
    
    messagesBox.innerHTML += `
        <div class="message user">
            <p>${msg}</p>
            <span class="time">Just now</span>
        </div>
    `;
    messagesBox.scrollTop = messagesBox.scrollHeight;

    const thinkingId = "thinking-" + Date.now();
    messagesBox.innerHTML += `
        <div class="message mentor" id="${thinkingId}">
            <p><i class="fa-solid fa-spinner fa-spin"></i> Coach is thinking...</p>
        </div>
    `;
    messagesBox.scrollTop = messagesBox.scrollHeight;

    try {
        let reply = "";
        if (appMode === "sandbox") {
            // Local offline mentor logic
            const q = msg.toLowerCase();
            if (q.includes("docker")) {
                reply = "For a dockerized Express backend, utilize a multi-stage Docker build separating dev dependencies from runtime modules. Mount local volumes for live hot-reloading. Here is a baseline structure:\n\n```\nFROM node:18-alpine AS build\nWORKDIR /app\nCOPY package.json .\nRUN npm install\nCOPY . .\n\nCMD [\"npm\", \"run\", \"dev\"]\n```";
            } else if (q.includes("resume") || q.includes("cv")) {
                reply = "To pass the ATS checks, ensure you compile using standard columns. Do not use floating graphics or charts that confuse text parsers. Quantify achievements with concrete figures (e.g. 'Improved DB read efficiency by 30%').";
            } else if (q.includes("hackathon") || q.includes("mvp")) {
                reply = "During hackathons, speed is critical. Focus on building a vertical slice of one core feature. Deploy early to Railway, and structure your pitch around the problem statement, database relational map, and future API expandability.";
            } else {
                reply = "That is a solid question. In software engineering, prioritize modularity and validation. Write clean functions, validate parameters using Pydantic, and log outputs securely. What specific component of this stack are you currently building?";
            }
            
            setTimeout(() => {
                document.getElementById(thinkingId).remove();
                messagesBox.innerHTML += `
                    <div class="message mentor">
                        <p>${reply}</p>
                        <span class="time">Just now</span>
                    </div>
                `;
                messagesBox.scrollTop = messagesBox.scrollHeight;
            }, 800);
        } else {
            const res = await API.sendMentorMessage(msg);
            document.getElementById(thinkingId).remove();
            
            messagesBox.innerHTML += `
                <div class="message mentor">
                    <p>${res.reply}</p>
                    <span class="time">Just now</span>
                </div>
            `;
            messagesBox.scrollTop = messagesBox.scrollHeight;
        }
    } catch (e) {
        document.getElementById(thinkingId).innerHTML = `<p class="text-red">Error: Server connection failed.</p>`;
    }
}

// --- MOCK INTERVIEW ACTIONS ---
function loadMockInterviewView() {
    document.getElementById("mock-setup-window").classList.remove("hidden");
    document.getElementById("mock-active-window").classList.add("hidden");
    mockInterviewState.active = false;
}

function startMockInterview() {
    const role = document.getElementById("mock-role-input").value.trim();
    if (!role) {
        alert("Please enter a target role.");
        return;
    }
    
    mockInterviewState.role = role;
    mockInterviewState.active = true;
    mockInterviewState.questionIndex = 0;
    mockInterviewState.answers = [];

    document.getElementById("mock-setup-window").classList.add("hidden");
    document.getElementById("mock-active-window").classList.remove("hidden");
    
    loadNextMockQuestion();
}

function loadNextMockQuestion() {
    const countText = document.getElementById("mock-question-counter");
    const questionText = document.getElementById("mock-question-text");
    const ansInput = document.getElementById("mock-answer-input");
    
    ansInput.value = "";
    document.getElementById("mock-feedback-box").classList.add("hidden");
    
    countText.innerText = `Question ${mockInterviewState.questionIndex + 1} of ${mockInterviewState.questions.length}`;
    questionText.innerText = mockInterviewState.questions[mockInterviewState.questionIndex];
    
    const submitBtn = document.getElementById("mock-submit-btn");
    submitBtn.innerHTML = `Submit Answer <i class="fa-solid fa-paper-plane"></i>`;
    submitBtn.onclick = () => submitMockAnswer();
}

async function submitMockAnswer() {
    const answer = document.getElementById("mock-answer-input").value.trim();
    if (!answer) {
        alert("Please type a response before submitting.");
        return;
    }

    const submitBtn = document.getElementById("mock-submit-btn");
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Grading...`;
    
    try {
        let explanation = "";
        
        if (appMode === "sandbox") {
            const idx = mockInterviewState.questionIndex;
            if (idx === 0) {
                explanation = "Good description. TCP guarantees packet delivery via acknowledgments, making it ideal for web browsing. UDP is connectionless and faster, suited for video streaming where loss is tolerable.";
            } else if (idx === 1) {
                explanation = "Excellent! SQL Injection is prevented via parametrized queries. Avoid raw SQL concatenation. Securing inputs with validator libraries is also critical.";
            } else {
                explanation = "Index tables improve read times but slow write operations. Maintain indices only for high-frequency search fields.";
            }
            
            setTimeout(() => {
                const feedbackBox = document.getElementById("mock-feedback-box");
                document.getElementById("mock-item-score").innerText = "85/100";
                document.getElementById("mock-item-desc").innerText = explanation;
                feedbackBox.classList.remove("hidden");

                submitBtn.innerHTML = `Next Question <i class="fa-solid fa-arrow-right"></i>`;
                submitBtn.onclick = () => moveToNextQuestion();
            }, 800);
        } else {
            const contextPrompt = `Evaluate mock interview answer. Question: "${mockInterviewState.questions[mockInterviewState.questionIndex]}". Answer: "${answer}". Score out of 100, and give improvement advice.`;
            const res = await API.sendMentorMessage(contextPrompt);
            
            const feedbackBox = document.getElementById("mock-feedback-box");
            document.getElementById("mock-item-score").innerText = "80/100";
            document.getElementById("mock-item-desc").innerText = res.reply;
            feedbackBox.classList.remove("hidden");

            submitBtn.innerHTML = `Next Question <i class="fa-solid fa-arrow-right"></i>`;
            submitBtn.onclick = () => moveToNextQuestion();
        }
    } catch (e) {
        alert("Failed to grade answer: " + e.message);
        submitBtn.innerHTML = `Submit Answer <i class="fa-solid fa-paper-plane"></i>`;
    }
}

function moveToNextQuestion() {
    mockInterviewState.questionIndex++;
    if (mockInterviewState.questionIndex < mockInterviewState.questions.length) {
        loadNextMockQuestion();
    } else {
        alert("Mock Interview Complete! Excellent work. You've earned 150 XP.");
        
        // Award XP locally
        if (appMode === "sandbox") {
            currentUser.xp += 150;
            localStorage.setItem("campusmate_sandbox_user", JSON.stringify(currentUser));
        }
        
        loadMockInterviewView();
        loadDashboard();
    }
}

function abortMockInterview() {
    if (confirm("Are you sure you want to end this interview session? Your progress will not be saved.")) {
        loadMockInterviewView();
    }
}

// --- HACKATHON CONCEPT ENGINE ---
function loadHackathonView() {
    document.getElementById("hackathon-output-container").classList.add("hidden");
    document.getElementById("hackathon-theme").value = "";
}

async function generateHackathonConcept() {
    const theme = document.getElementById("hackathon-theme").value.trim();
    if (!theme) {
        alert("Please enter a hackathon theme.");
        return;
    }
    
    const outputContainer = document.getElementById("hackathon-output-container");
    const markdownOutput = document.getElementById("hackathon-markdown-output");
    
    markdownOutput.innerHTML = `<div class="empty-state"><i class="fa-solid fa-spinner fa-spin fa-2xl mb-10"></i><p>Formulating prototype MVP, PPT structures, and folders templates...</p></div>`;
    outputContainer.classList.remove("hidden");

    try {
        let reply = "";
        
        if (appMode === "sandbox") {
            // Offline mock concept generator
            reply = `<h2>Hackathon Project Blueprint: ${theme}</h2>
            <h3>1. MVP Architecture Overview</h3>
            <pre><code>[Frontend: HTML5/JS] ---> [FastAPI App Server] ---> [SQLite Storage]</code></pre>
            
            <h3>2. Tech Stack & Library Configurations</h3>
            <ul>
                <li><strong>Language:</strong> Python 3.12, Javascript ES6</li>
                <li><strong>Backend:</strong> FastAPI, SQLModel (ORM)</li>
                <li><strong>Styling:</strong> Vanilla CSS with custom layouts variables</li>
            </ul>
            
            <h3>3. Presentation Pitch Outline</h3>
            <ul>
                <li><strong>Slide 1:</strong> Problem statement & current market inefficiencies.</li>
                <li><strong>Slide 2:</strong> Solution architecture & demo overview.</li>
                <li><strong>Slide 3:</strong> Future roadmap & API expandability layers.</li>
            </ul>`;
            
            setTimeout(() => {
                markdownOutput.innerHTML = reply;
            }, 800);
        } else {
            const prompt = `Generate a Hackathon blueprint concept for theme: "${theme}". Outline: 1. MVP Concept 2. Database Schema 3. Tech Stack 4. Step-by-Step implementation plan 5. Presentation Pitch Deck structure.`;
            const res = await API.sendMentorMessage(prompt);
            
            let parsedHtml = res.reply
                .replace(/### (.*)/g, '<h3>$1</h3>')
                .replace(/## (.*)/g, '<h2>$1</h2>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
                .replace(/- (.*)/g, '<li>$1</li>');
                
            markdownOutput.innerHTML = parsedHtml;
        }
    } catch (e) {
        alert("Failed to generate hackathon concept: " + e.message);
        outputContainer.classList.add("hidden");
    }
}

function closeHackathonOutput() {
    document.getElementById("hackathon-output-container").classList.add("hidden");
}
