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
    setupResumeUploadDragAndDrop();
    
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
    let nodes = [];
    
    if (role === "Cyber Security") {
        nodes = [
            {
                id: "node-1",
                title: "Network Protocols & Packet Analysis",
                description: "Master TCP/IP, DNS, HTTP/S, and packet capture tools like Wireshark.",
                difficulty: "BEGINNER",
                estimated_duration: "12 hours",
                resources: [{title: "Wireshark Labs & Tutorials", url: "https://www.wireshark.org"}],
                projects: [{title: "Packet Trace Audit", description: "Capture local interface traffic and analyze TLS handshake messages.", tasks: ["Install packet analyzer", "Capture HTTP vs HTTPS payloads", "Extract handshake metadata"]}],
                certifications: [{name: "CompTIA Network+", provider: "CompTIA"}],
                status: "AVAILABLE"
            },
            {
                id: "node-2",
                title: "Linux Administration & OS Hardening",
                description: "Configure system permissions, service policies, audit log entries, and SSH secure tunnels.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "15 hours",
                resources: [{title: "Linux Hardening Guidelines", url: "https://www.cisecurity.org"}],
                projects: [{title: "Secure Bastion Server Setup", description: "Deploy a Linux kernel VM, disable root SSH logins, and block unauthorized ports.", tasks: ["Establish firewall policies", "Setup logging daemon auditd", "Configure SSH key authentication"]}],
                certifications: [{name: "CompTIA Security+", provider: "CompTIA"}],
                status: "LOCKED"
            },
            {
                id: "node-3",
                title: "OWASP Top 10 & Web Pentesting",
                description: "Test web gateways against SQL Injection, Cross-Site Scripting (XSS), and Broken Authentication.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "20 hours",
                resources: [{title: "OWASP Web Security Testing Guide", url: "https://owasp.org"}],
                projects: [{title: "Vulnerable App Vulnerability Assessment", description: "Run automated and manual audits on test nodes, detailing severity findings.", tasks: ["Run OWASP ZAP scanners", "Examine CORS configuration logs", "Draft remediation script proposals"]}],
                certifications: [{name: "Certified Ethical Hacker (CEH)", provider: "EC-Council"}],
                status: "LOCKED"
            },
            {
                id: "node-4",
                title: "Cloud Security, Identity & Governance",
                description: "Learn cloud IAM structures, VPC security groups, key management vaults, and identity federation.",
                difficulty: "ADVANCED",
                estimated_duration: "24 hours",
                resources: [{title: "Microsoft Learn: Security, Compliance, and Identity", url: "https://learn.microsoft.com"}],
                projects: [{title: "Zero-Trust Cloud Network", description: "Design an Azure/AWS virtual private network with restricted IAM policies and network firewalls.", tasks: ["Define narrow security group rules", "Enable Azure Key Vault auditing", "Restrict database access to VPC CIDR"]}],
                certifications: [{name: "Microsoft Certified: Cybersecurity Architect Expert", provider: "Microsoft"}],
                status: "LOCKED"
            }
        ];
    } else if (role === "AI Engineering") {
        nodes = [
            {
                id: "node-1",
                title: "Linear Algebra & Calculus for AI",
                description: "Learn matrices multiplication, eigenvalues, partial gradients, and optimization rules.",
                difficulty: "BEGINNER",
                estimated_duration: "14 hours",
                resources: [{title: "3Blue1Brown: Essence of Linear Algebra", url: "https://www.youtube.com"}],
                projects: [{title: "Gradient Descent Simulator", description: "Code linear regression gradients optimization from scratch in pure Python.", tasks: ["Setup loss function metrics", "Implement matrix operations manually", "Plot learning rates gradient graphs"]}],
                certifications: [{name: "DeepLearning.AI Math for Machine Learning", provider: "Coursera"}],
                status: "AVAILABLE"
            },
            {
                id: "node-2",
                title: "Machine Learning Classifiers & Pipelines",
                description: "Train decision trees, random forests, SVN classifiers, and evaluate validation scores.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "18 hours",
                resources: [{title: "Scikit-Learn Tutorials", url: "https://scikit-learn.org"}],
                projects: [{title: "Customer Churn Classifiers Pipeline", description: "Build data cleaning, scaling, and training pipelines on scikit-learn libraries.", tasks: ["Run cross validation folds", "Compare precision-recall ratios", "Export models using Joblib serialization"]}],
                certifications: [{name: "Google Cloud: Machine Learning Engineer", provider: "Google"}],
                status: "LOCKED"
            },
            {
                id: "node-3",
                title: "Deep Neural Networks & PyTorch",
                description: "Configure multi-layer perceptrons, backpropagation graphs, activation rules, and optimizers.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "22 hours",
                resources: [{title: "PyTorch Basics & Tutorials", url: "https://pytorch.org"}],
                projects: [{title: "MNIST Digit Recognition Network", description: "Write convolutional neural network layers using PyTorch frameworks, evaluating accuracy.", tasks: ["Setup DataLoader generators", "Tune learning rate decays", "Plot training loss curves"]}],
                certifications: [{name: "Microsoft Certified: Azure AI Engineer Associate", provider: "Microsoft"}],
                status: "LOCKED"
            },
            {
                id: "node-4",
                title: "LLMs, Vector Databases & RAG Architectures",
                description: "Master prompt engineering templates, semantic text embeddings, vector matching databases, and LangChain hooks.",
                difficulty: "ADVANCED",
                estimated_duration: "26 hours",
                resources: [{title: "DeepLearning.AI: Prompt Engineering Guides", url: "https://www.deeplearning.ai"}],
                projects: [{title: "Document Assistant using RAG", description: "Build a document scraper that queries vector stores and structures response summaries using Gemini APIs.", tasks: ["Chunk document texts", "Index in vector stores", "Design LLM response wrappers"]}],
                certifications: [{name: "TensorFlow Developer Certificate", provider: "Google"}],
                status: "LOCKED"
            }
        ];
    } else if (role === "Machine Learning") {
        nodes = [
            {
                id: "node-1",
                title: "Python Math Libraries: NumPy & Pandas",
                description: "Manipulate multi-dimensional arrays, data frames indexing, filtering, and aggregation.",
                difficulty: "BEGINNER",
                estimated_duration: "10 hours",
                resources: [{title: "Pandas User Guides", url: "https://pandas.pydata.org"}],
                projects: [{title: "Academic Performance Profiler", description: "Clean datasets, handle missing coordinates, and output aggregate statistics summaries.", tasks: ["Merge relational CSV arrays", "Compute group variance statistics", "Plot performance histogram distributions"]}],
                certifications: [{name: "IBM Data Science Professional Certificate", provider: "IBM"}],
                status: "AVAILABLE"
            },
            {
                id: "node-2",
                title: "Supervised Learning Regression Models",
                description: "Analyze linear, ridge, lasso regressions, and calculate mean squared error variances.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "14 hours",
                resources: [{title: "Introduction to Statistical Learning", url: "https://statlearning.com"}],
                projects: [{title: "Housing Price Estimators", description: "Tune multi-feature regression functions, checking residuals distribution logs.", tasks: ["Clean outlier outliers", "Normalize dynamic ranges", "Calculate coefficient of determination"]}],
                certifications: [{name: "Stanford Machine Learning Certification", provider: "Coursera"}],
                status: "LOCKED"
            },
            {
                id: "node-3",
                title: "Unsupervised Clustering & Dimensions Compression",
                description: "Master K-Means algorithms, Hierarchical clustering, and Principal Component Analysis (PCA).",
                difficulty: "INTERMEDIATE",
                estimated_duration: "18 hours",
                resources: [{title: "Scikit-Learn Clustering Documentation", url: "https://scikit-learn.org"}],
                projects: [{title: "Market Segments Clustering Explorer", description: "Perform PCA dimensions compression and map customer clusters using K-Means.", tasks: ["Determine cluster counts via elbow metrics", "Run dimensional projection charts", "Detail characteristic features per cluster"]}],
                certifications: [{name: "AWS Certified Machine Learning - Specialty", provider: "Amazon"}],
                status: "LOCKED"
            },
            {
                id: "node-4",
                title: "MLOps Pipelines & Model Registry",
                description: "Learn model version tracking, artifact staging, container packaging, and automated retraining.",
                difficulty: "ADVANCED",
                estimated_duration: "24 hours",
                resources: [{title: "MLflow Documentation & Guides", url: "https://mlflow.org"}],
                projects: [{title: "Model Production Delivery System", description: "Register target models, package using FastAPI wrappers, and configure CI auto-build containers.", tasks: ["Setup model version registries", "Define REST request parsing", "Run continuous inference tests"]}],
                certifications: [{name: "Google Cloud Professional ML Engineer", provider: "Google"}],
                status: "LOCKED"
            }
        ];
    } else if (role === "Data Science") {
        nodes = [
            {
                id: "node-1",
                title: "SQL Querying & Data Restructuring",
                description: "Master subqueries, inner/outer joins, window functions, and data schema normalization.",
                difficulty: "BEGINNER",
                estimated_duration: "10 hours",
                resources: [{title: "PostgreSQL Tutorial Core Guides", url: "https://www.postgresqltutorial.com"}],
                projects: [{title: "Multi-Store Transactions Database Analysis", description: "Write complex window queries to extract monthly metrics.", tasks: ["Construct relational schema structures", "Write aggregate rollup calculations", "Format report tables"]}],
                certifications: [{name: "Google Data Analytics Professional", provider: "Google"}],
                status: "AVAILABLE"
            },
            {
                id: "node-2",
                title: "Exploratory Data Analysis & Vis",
                description: "Design reports, trace correlations using Seaborn, and explain skewness patterns.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "12 hours",
                resources: [{title: "Seaborn Visualization Guide", url: "https://seaborn.pydata.org"}],
                projects: [{title: "SaaS Performance Dashboard Plots", description: "Generate distribution heatmaps and scatter-correlation charts from raw customer events.", tasks: ["Clean duplicate event arrays", "Plot daily retention heatmaps", "Verify correlation coefficients metrics"]}],
                certifications: [{name: "Microsoft Certified: Power BI Data Analyst", provider: "Microsoft"}],
                status: "LOCKED"
            },
            {
                id: "node-3",
                title: "Statistical Methods & Hypothesis Audits",
                description: "Apply Z-scores, T-tests, ANOVA calculations, p-values verification, and Central Limit theorems.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "16 hours",
                resources: [{title: "OpenStax Introductory Statistics", url: "https://openstax.org"}],
                projects: [{title: "A/B Conversion Testing Analysis", description: "Calculate conversions variances between test designs, checking statistical significance ratios.", tasks: ["Establish null hypothesis assumptions", "Compute standard errors ratios", "Determine final p-value outputs"]}],
                certifications: [{name: "IBM Applied Data Science Specialist", provider: "IBM"}],
                status: "LOCKED"
            },
            {
                id: "node-4",
                title: "Big Data Pipelines & Apache Spark",
                description: "Write PySpark scripts, map MapReduce keys, partition datasets, and run distributed jobs.",
                difficulty: "ADVANCED",
                estimated_duration: "22 hours",
                resources: [{title: "Apache Spark Programming Guide", url: "https://spark.apache.org"}],
                projects: [{title: "Log Event Scraper using Spark", description: "Parse 10M rows of system event logs, outputting target errors distributions.", tasks: ["Set up PySpark session configurations", "Partition server datasets", "Aggregate error traces daily"]}],
                certifications: [{name: "Cloudera Certified Associate: Data Analyst", provider: "Cloudera"}],
                status: "LOCKED"
            }
        ];
    } else if (role === "Cloud Computing") {
        nodes = [
            {
                id: "node-1",
                title: "Networking & Cloud Basics",
                description: "Learn subnets masking, DNS zones, HTTP load balancers, and standard cloud storage classes.",
                difficulty: "BEGINNER",
                estimated_duration: "10 hours",
                resources: [{title: "AWS Technical Essentials", url: "https://aws.amazon.com"}],
                projects: [{title: "Static CDN Portfolio Website", description: "Deploy front-end layouts to object stores behind secure SSL content networks.", tasks: ["Create cloud storage buckets", "Configure custom domain routing", "Enable cache invalidations profiles"]}],
                certifications: [{name: "AWS Certified Cloud Practitioner", provider: "Amazon"}],
                status: "AVAILABLE"
            },
            {
                id: "node-2",
                title: "Infrastructure as Code & Terraform",
                description: "Define cloud states, write resource blocks, configure outputs, and organize module patterns.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "15 hours",
                resources: [{title: "Terraform HashiCorp Tutorials", url: "https://learn.hashicorp.com"}],
                projects: [{title: "Automated AWS/Azure VPC Blueprint", description: "Write Terraform files defining target network components, security groups, and virtual instances.", tasks: ["Setup remote state configuration stores", "Define security boundary parameters", "Test plan deployments"]}],
                certifications: [{name: "HashiCorp Certified: Terraform Associate", provider: "HashiCorp"}],
                status: "LOCKED"
            },
            {
                id: "node-3",
                title: "Serverless Deployments & API Gateways",
                description: "Write function runtimes, handle cold starts, configure route integrations, and authorize users.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "18 hours",
                resources: [{title: "Serverless Framework Guides", url: "https://www.serverless.com"}],
                projects: [{title: "Serverless User Registration Endpoint", description: "Create Lambda handlers writing profile entries into DynamoDB arrays.", tasks: ["Write serverless template configurations", "Add JSON validator middleware layers", "Test endpoints routing rules"]}],
                certifications: [{name: "Microsoft Certified: Azure Developer Associate", provider: "Microsoft"}],
                status: "LOCKED"
            },
            {
                id: "node-4",
                title: "Multi-Cloud Architectures & VPC Peering",
                description: "Configure VPN tunnels, VPC peering connections, route tables, and unified cloud governance.",
                difficulty: "ADVANCED",
                estimated_duration: "24 hours",
                resources: [{title: "AWS Well-Architected Framework", url: "https://aws.amazon.com"}],
                projects: [{title: "High Availability Web Stack", description: "Deploy virtual scale sets across regions behind redundant load balancers.", tasks: ["Setup multi-region database replications", "Configure auto-scaling thresholds", "Run chaos network simulation tests"]}],
                certifications: [{name: "AWS Certified Solutions Architect - Professional", provider: "Amazon"}],
                status: "LOCKED"
            }
        ];
    } else if (role === "DevOps") {
        nodes = [
            {
                id: "node-1",
                title: "Linux Shell Scripting & Systems Commands",
                description: "Automate system actions, parse text streams, setup cron schedules, and verify logs.",
                difficulty: "BEGINNER",
                estimated_duration: "10 hours",
                resources: [{title: "Linux Command Line Core Tutorial", url: "https://linuxjourney.com"}],
                projects: [{title: "System Performance Logger", description: "Write a bash shell script collecting memory statistics and writing alert logs.", tasks: ["Parse top metrics arrays", "Setup systemd cron triggers", "Email error summaries"]}],
                certifications: [{name: "Linux Professional Institute LPIC-1", provider: "LPI"}],
                status: "AVAILABLE"
            },
            {
                id: "node-2",
                title: "Containerization using Docker",
                description: "Build custom Docker images, write optimization rules, mount host files, and configure network links.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "14 hours",
                resources: [{title: "Docker Get Started guides", url: "https://docs.docker.com"}],
                projects: [{title: "Multi-Container Development Sandbox", description: "Assemble compose configuration files connecting python app servers, Redis layers, and Postgres storage databases.", tasks: ["Optimize image layers definitions", "Link secure container subnets", "Define volume persistent mappings"]}],
                certifications: [{name: "Docker Certified Associate (DCA)", provider: "Mirantis"}],
                status: "LOCKED"
            },
            {
                id: "node-3",
                title: "Continuous Integrations (CI/CD) and GitHub Actions",
                description: "Automate test suites execution, run syntax linters, compile binaries, and publish container registries.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "16 hours",
                resources: [{title: "GitHub Actions documentation", url: "https://docs.github.com"}],
                projects: [{title: "Automated Release Pipeline", description: "Write continuous actions workflows compiling code, passing verification tests, and deploying on cloud nodes.", tasks: ["Establish step-by-step workflow definitions", "Mask API auth credentials", "Release Docker image releases"]}],
                certifications: [{name: "GitHub Actions Certification", provider: "GitHub"}],
                status: "LOCKED"
            },
            {
                id: "node-4",
                title: "Container Orchestration with Kubernetes",
                description: "Configure pods mappings, cluster networks, volume mounts, ingress routes, and auto-scalers.",
                difficulty: "ADVANCED",
                estimated_duration: "24 hours",
                resources: [{title: "Kubernetes interactive training tutorials", url: "https://kubernetes.io"}],
                projects: [{title: "Zero-Downtime Microservices Web App", description: "Write Kubernetes manifest files, routing live user sessions across scaled pods clusters.", tasks: ["Define cluster deployment configs", "Set CPU/Memory resources thresholds", "Test rolling updates processes"]}],
                certifications: [{name: "Certified Kubernetes Administrator (CKA)", provider: "Cloud Native Computing Foundation"}],
                status: "LOCKED"
            }
        ];
    } else if (role === "Full Stack Development" || role === "Full Stack Web Developer" || role === "Full Stack") {
        nodes = [
            {
                id: "node-1",
                title: "Web Essentials: HTML5, CSS3, & Modern JS",
                description: "Learn semantic layout design, responsive media rules, and ES6 asynchronous callbacks.",
                difficulty: "BEGINNER",
                estimated_duration: "10 hours",
                resources: [{title: "MDN Web Development Guides", url: "https://developer.mozilla.org"}],
                projects: [{title: "Dynamic Student Operating Dashboard", description: "Build a single page app using HTML layouts, responsive grids, and mock states.", tasks: ["Organize flex layout cards", "Write data filter selectors", "Store values in localStorage arrays"]}],
                certifications: [{name: "FreeCodeCamp Responsive Web Design", provider: "FreeCodeCamp"}],
                status: "AVAILABLE"
            },
            {
                id: "node-2",
                title: "Front-end Frameworks & Client States",
                description: "Build reusable UI components, manage global states, route views, and handle API requests.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "16 hours",
                resources: [{title: "React.js official documentation", url: "https://react.dev"}],
                projects: [{title: "Collaborative Project Management UI", description: "Design a kanban-style project board with reactive state transitions.", tasks: ["Write modular interface components", "Implement drag-and-drop state sync", "Authenticate users routing gates"]}],
                certifications: [{name: "Meta Front-End Developer Certificate", provider: "Meta"}],
                status: "LOCKED"
            },
            {
                id: "node-3",
                title: "Backend API Servers with FastAPI",
                description: "Define HTTP endpoint routes, write validation schemas, verify tokens, and handle exceptions.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "18 hours",
                resources: [{title: "FastAPI Tutorials & Guides", url: "https://fastapi.tiangolo.com"}],
                projects: [{title: "Document Vault REST API", description: "Create backend routes storing metadata records in persistent relational databases.", tasks: ["Write pydantic request schemas", "Enforce JWT authentication tokens", "Structure route controllers logic"]}],
                certifications: [{name: "GitHub Foundations", provider: "GitHub"}],
                status: "LOCKED"
            },
            {
                id: "node-4",
                title: "Database Performance Tuning & Deployment",
                description: "Optimize SQL joins, configure connection pools, write index rules, and package in containers.",
                difficulty: "ADVANCED",
                estimated_duration: "20 hours",
                resources: [{title: "PostgreSQL Performance Optimization", url: "https://pgmustard.com"}],
                projects: [{title: "Scalable SaaS Stack", description: "Deploy database persistent schemas, connect backend services, and release live systems via GitHub.", tasks: ["Write optimize database index queries", "Build Docker multi-stage images", "Configure Railway release pipelines"]}],
                certifications: [{name: "Microsoft Certified: Azure Developer Associate", provider: "Microsoft"}],
                status: "LOCKED"
            }
        ];
    } else { // Mobile Development
        nodes = [
            {
                id: "node-1",
                title: "Mobile UI Design Principles",
                description: "Learn human interface guidelines, view hierarchies, flex layouts, and responsive alignments.",
                difficulty: "BEGINNER",
                estimated_duration: "10 hours",
                resources: [{title: "Apple Human Interface Guidelines", url: "https://developer.apple.com"}],
                projects: [{title: "Task Planner UI Mockups", description: "Draft responsive interface layouts with smooth transitions.", tasks: ["Sketch layout wireframes", "Implement custom buttons grids", "Create tab views navigation"]}],
                certifications: [{name: "Google UX Design Professional Certificate", provider: "Google"}],
                status: "AVAILABLE"
            },
            {
                id: "node-2",
                title: "Swift / Kotlin Fundamentals",
                description: "Master optional values, object types, memory delegation patterns, and asynchronous routines.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "16 hours",
                resources: [{title: "Swift Programming Language documentation", url: "https://swift.org"}],
                projects: [{title: "Local File Manager App Utility", description: "Develop mobile application reading directories contents and writing JSON configuration scripts.", tasks: ["Setup class protocols definitions", "Configure file access permissions", "Test exception handlers cases"]}],
                certifications: [{name: "Meta iOS/Android Developer Certificate", provider: "Meta"}],
                status: "LOCKED"
            },
            {
                id: "node-3",
                title: "Asynchronous Networking & State Storage",
                description: "Fetch remote JSON arrays, handle network latency errors, and write values to offline local database stores.",
                difficulty: "INTERMEDIATE",
                estimated_duration: "18 hours",
                resources: [{title: "Kotlin Coroutines Guide", url: "https://kotlinlang.org"}],
                projects: [{title: "Real-time Weather Forecast Dashboard", description: "Query remote meteorological services API, caching updates locally in SQLite repositories.", tasks: ["Write async fetch controllers", "Serialize JSON data arrays", "Sync offline database registries"]}],
                certifications: [{name: "Google Associate Android Developer", provider: "Google"}],
                status: "LOCKED"
            },
            {
                id: "node-4",
                title: "App Publishing Pipelines & CI/CD Release",
                description: "Configure provisioning certs, compile target packages, run tests, and publish via App Store pipelines.",
                difficulty: "ADVANCED",
                estimated_duration: "22 hours",
                resources: [{title: "Google Play Store publishing instructions", url: "https://developer.android.com"}],
                projects: [{title: "Continuous Release Mobile App", description: "Write GitHub actions workflows building target packages, running verification tests, and signing binaries.", tasks: ["Configure certificates encryption keys", "Write release actions configurations", "Build distribution packages"]}],
                certifications: [{name: "GitHub Actions Certification", provider: "GitHub"}],
                status: "LOCKED"
            }
        ];
    }

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
    
    // Load persisted chat history
    loadChatHistory();
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
        updateMentorMemoryBar();
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
    await executeMentorQuery(msg);
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function typeWriterEffect(element, html, callback) {
    let i = 0;
    const speed = 10; // milliseconds
    const step = 6;   // characters per tick
    element.innerHTML = "";
    const timer = setInterval(() => {
        if (i < html.length) {
            element.innerHTML = html.substring(0, i + step);
            i += step;
        } else {
            clearInterval(timer);
            element.innerHTML = html;
            if (callback) callback();
        }
    }, speed);
}

async function handleChipClick(text) {
    const drawer = document.getElementById("mentor-drawer");
    if (!drawer.classList.contains("active")) {
        toggleMentorDrawer();
    }
    await executeMentorQuery(text);
}

function updateSuggestionChips(lastQuery) {
    const q = lastQuery.toLowerCase();
    const container = document.getElementById("mentor-chat-chips");
    if (!container) return;
    
    let chips = [];
    if (q.includes("cert") || q.includes("credential")) {
        chips = [
            "How should I study for AZ-900?",
            "Recommend AWS practice projects",
            "Draft resume bullet points for certs"
        ];
    } else if (q.includes("project") || q.includes("recommend")) {
        chips = [
            "Draft backend Express files structure",
            "What database models should I use?",
            "Suggest a DevOps CI/CD workflow"
        ];
    } else if (q.includes("resume") || q.includes("cv") || q.includes("experience")) {
        chips = [
            "Explain Google XYZ formula",
            "Suggest rewrites for intern role",
            "How to add missing keywords"
        ];
    } else if (q.includes("docker") || q.includes("container")) {
        chips = [
            "Explain Docker multi-stage builds",
            "How to map host directory volumes",
            "Draft standard compose files"
        ];
    } else {
        chips = [
            "Recommend a project template",
            "What certifications fit my target track?",
            "Check my experience bullet points"
        ];
    }
    
    container.innerHTML = chips.map(c => `
        <button class="chip" onclick="handleChipClick('${c.replace(/'/g, "\\'")}')">${c}</button>
    `).join("");
}

function loadChatHistory() {
    const messagesBox = document.getElementById("mentor-chat-messages");
    if (!messagesBox) return;
    
    if (appMode === "sandbox") {
        const history = JSON.parse(localStorage.getItem("campusmate_sandbox_chat_history") || "[]");
        if (history.length > 0) {
            messagesBox.innerHTML = "";
            history.forEach(h => {
                const messageClass = h.sender === "user" ? "user" : "mentor";
                messagesBox.innerHTML += `
                    <div class="message ${messageClass}">
                        <p>${h.message}</p>
                        <span class="time">Just now</span>
                    </div>
                `;
            });
            messagesBox.scrollTop = messagesBox.scrollHeight;
        } else {
            messagesBox.innerHTML = `
                <div class="message mentor">
                    <p>Hello! I am your career mentor. Ask me questions about roadmaps, certifications, project architectures, or resumes!</p>
                    <span class="time">Just now</span>
                </div>
            `;
        }
    }
    updateMentorMemoryBar();
}

function updateMentorMemoryBar() {
    const el = document.getElementById("mentor-memory-text");
    if (!el || !currentUser) return;
    
    const role = currentUser.targetRole || "None selected";
    const xp = currentUser.xp || 100;
    const resumeScore = localStorage.getItem("campusmate_sandbox_resumescore") || 0;
    
    el.innerHTML = `Memory: Track: <strong>${role}</strong> | XP: <strong>${xp}</strong> | Resume: <strong>${resumeScore}%</strong>`;
}

async function executeMentorQuery(msg) {
    const messagesBox = document.getElementById("mentor-chat-messages");
    
    // Save history locally in Sandbox
    let history = [];
    if (appMode === "sandbox") {
        history = JSON.parse(localStorage.getItem("campusmate_sandbox_chat_history") || "[]");
    }
    
    messagesBox.innerHTML += `
        <div class="message user">
            <p>${escapeHtml(msg)}</p>
            <span class="time">Just now</span>
        </div>
    `;
    messagesBox.scrollTop = messagesBox.scrollHeight;

    if (appMode === "sandbox") {
        history.push({ sender: "user", message: msg });
        localStorage.setItem("campusmate_sandbox_chat_history", JSON.stringify(history));
    }

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
            const q = msg.toLowerCase();
            const role = currentUser.targetRole || "Software Engineering";
            const level = currentUser.academicLevel || "Undergraduate";
            const xp = currentUser.xp || 100;
            const resumeScore = localStorage.getItem("campusmate_sandbox_resumescore") || 0;

            if (q.includes("cert") || q.includes("credential")) {
                reply = `<h3>Matched Credentials for ${role}</h3>
                <p>Based on your profile (XP: ${xp}), I recommend targeting these high-value industry certifications:</p>
                <div class="project-info-box" style="margin-top:10px; background: rgba(15,23,42,0.02);">
                    <strong>1. GitHub Foundations</strong><br>
                    Difficulty: Beginner | Cost: $99 | Career Value: High<br>
                    <p style="font-size:12px; margin-top:4px; color:var(--text-secondary);">Validates your knowledge of Git workflows, version control, and collaboration.</p>
                </div>
                <div class="project-info-box" style="margin-top:10px; background: rgba(15,23,42,0.02);">
                    <strong>2. Microsoft Certified: Azure Fundamentals (AZ-900)</strong><br>
                    Difficulty: Beginner | Cost: $99 | Career Value: Very High<br>
                    <p style="font-size:12px; margin-top:4px; color:var(--text-secondary);">Demonstrates foundational cloud concepts, resource deployment, and governance mechanisms.</p>
                </div>
                <div class="project-info-box" style="margin-top:10px; background: rgba(15,23,42,0.02);">
                    <strong>3. AWS Cloud Practitioner</strong><br>
                    Difficulty: Beginner | Cost: $100 | Career Value: Very High<br>
                    <p style="font-size:12px; margin-top:4px; color:var(--text-secondary);">Excellent validation of AWS global infrastructure, core services, and pricing model.</p>
                </div>
                <p style="margin-top:10px;">Click standard Roadmap node detail overlays to match study links directly.</p>`;
            } else if (q.includes("project") || q.includes("recommend")) {
                reply = `<h3>Capstone Project Blueprint: ${role}</h3>
                <p>Here is a premium portfolio project configured for your current track:</p>
                <div class="project-info-box" style="margin-top:10px; background: rgba(15,23,42,0.02);">
                    <strong>Interactive SaaS Portal with FastAPI</strong><br>
                    <p style="font-size:12px; margin-top:4px; color:var(--text-secondary);">Develop a responsive single-page web app with backend auth, SQLModel relations, and fully automated deployment.</p>
                    <ul style="font-size:12px; margin-left: 15px; margin-top: 6px;">
                        <li>Task 1: Set up modular folder design and SQLite persistence schema.</li>
                        <li>Task 2: Implement asynchronous API controllers and JWT bearer tokens.</li>
                        <li>Task 3: Package in Docker containers and release via continuous Railway actions.</li>
                    </ul>
                </div>
                <p style="margin-top:10px;">Would you like me to generate a script outline or directory tree for this project?</p>`;
            } else if (q.includes("resume") || q.includes("cv") || q.includes("experience")) {
                reply = `<h3>Resume Diagnostic & Keyword Audit</h3>
                <p>Your current resume score is <strong>${resumeScore}/100</strong>.</p>
                <p>To improve recruiter readability and pass keyword filters, apply these recommendations:</p>
                <ul style="margin-left:15px; margin-top:5px; font-size:13px; line-height:1.6;">
                    <li>Apply the <strong>Google XYZ formula</strong>: 'Accomplished [X] as measured by [Y], by doing [Z]'. Use exact metrics!</li>
                    <li>Avoid floating graphical design systems. Stick to clean, printable single-column formats.</li>
                    <li>Add these missing keywords directly: <strong>Docker, PostgreSQL, FastAPI, Git version control</strong>.</li>
                </ul>`;
            } else if (q.includes("docker")) {
                reply = `<h3>Docker Containers Deployment</h3>
                <p>For a dockerized Node/Express backend, utilize a multi-stage Docker build separating dev dependencies from runtime modules. Mount local volumes for live hot-reloading.</p>
<pre style="background:rgba(15,23,42,0.04); padding:10px; border-radius:6px; margin:10px 0; overflow-x:auto;"><code>FROM node:18-alpine AS build
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
CMD ["npm", "run", "dev"]</code></pre>`;
            } else if (q.includes("hackathon") || q.includes("mvp")) {
                reply = "During hackathons, speed is critical. Focus on building a vertical slice of one core feature. Deploy early to Railway, and structure your pitch around the problem statement, database relational map, and future API expandability.";
            } else {
                reply = `As your career mentor, I am tracking your target role of **${role}** at the **${level}** level. 
                To progress efficiently, focus on finishing your active roadmap milestones and verifying your learning with mini-projects.
                
                What specific technical stack, code, or architecture design details would you like to build today?`;
            }

            setTimeout(() => {
                document.getElementById(thinkingId).remove();
                
                const mentorMsgId = "mentor-msg-" + Date.now();
                messagesBox.innerHTML += `
                    <div class="message mentor" id="${mentorMsgId}">
                        <p></p>
                        <span class="time">Just now</span>
                    </div>
                `;
                messagesBox.scrollTop = messagesBox.scrollHeight;
                
                const targetMsgEl = document.querySelector(`#${mentorMsgId} p`);
                typeWriterEffect(targetMsgEl, reply, () => {
                    history.push({ sender: "mentor", message: reply });
                    localStorage.setItem("campusmate_sandbox_chat_history", JSON.stringify(history));
                    messagesBox.scrollTop = messagesBox.scrollHeight;
                    updateSuggestionChips(msg);
                });

            }, 800);
        } else {
            const res = await API.sendMentorMessage(msg);
            document.getElementById(thinkingId).remove();
            
            const mentorMsgId = "mentor-msg-" + Date.now();
            messagesBox.innerHTML += `
                <div class="message mentor" id="${mentorMsgId}">
                    <p></p>
                    <span class="time">Just now</span>
                </div>
            `;
            messagesBox.scrollTop = messagesBox.scrollHeight;
            
            const targetMsgEl = document.querySelector(`#${mentorMsgId} p`);
            typeWriterEffect(targetMsgEl, res.reply, () => {
                messagesBox.scrollTop = messagesBox.scrollHeight;
                updateSuggestionChips(msg);
            });
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

function setupResumeUploadDragAndDrop() {
    const zone = document.getElementById("resume-drag-drop-zone");
    const input = document.getElementById("resume-file-input");
    if (!zone || !input) return;

    // Click to select file
    zone.addEventListener("click", () => {
        input.click();
    });

    // Handle file selection
    input.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleUploadedResume(e.target.files[0]);
        }
    });

    // Drag events
    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("drag-over");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("drag-over");
    });

    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("drag-over");
        if (e.dataTransfer.files.length > 0) {
            handleUploadedResume(e.dataTransfer.files[0]);
        }
    });
}

async function handleUploadedResume(file) {
    const statusText = document.getElementById("upload-status-text");
    if (!statusText) return;

    statusText.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing & parsing "${file.name}"...`;
    
    try {
        let response = null;
        if (appMode === "sandbox") {
            // Simulate sandbox file upload parse delay
            await new Promise(resolve => setTimeout(resolve, 1200));
            
            // Build sandbox mock resume from file name
            const fnLower = file.name.toLowerCase();
            let parsedName = "Alex Smith";
            let parsedEmail = "alex.smith@university.edu";
            let parsedRole = "Software Engineering Intern";
            let parsedExpDesc = "Responsible for coding the backend of the student project application. Helped team build website.";
            let parsedProjTitle = "Distributed Document Scraper";
            let parsedProjDesc = "Wrote backend scripts to parse directories. Integrated database mapping.";
            let keywords = ["Git", "REST APIs", "Uvicorn", "Postgres"];
            
            if (fnLower.includes("cyber") || fnLower.includes("security")) {
                parsedRole = "Security Analyst Intern";
                parsedExpDesc = "Conducted vulnerability assessments using Wireshark and network security audits.";
                parsedProjTitle = "Bastion Firewall Setup";
                parsedProjDesc = "Configured SSH tunnels, iptables protocols, and log auditing policies.";
                keywords = ["Wireshark", "Nmap", "Metasploit", "Penetration Testing"];
            } else if (fnLower.includes("ai") || fnLower.includes("machine") || fnLower.includes("ml")) {
                parsedRole = "ML/AI Engineering Intern";
                parsedExpDesc = "Constructed data preprocessing pipelines and trained neural networks models.";
                parsedProjTitle = "RAG Document Assistant";
                parsedProjDesc = "Configured vector stores matching and structured Gemini API request prompts.";
                keywords = ["FastAPI", "Docker", "SQLModel", "Gemini API"];
            }

            const analysisData = {
                score: 78,
                missingKeywords: keywords,
                improvements: [
                    {
                        originalText: parsedExpDesc,
                        suggestedText: `Optimized backend workflows using standard tools, reducing resource utilization metrics by 25%.`,
                        reason: "Uses exact technical stacks and metric goals."
                    }
                ]
            };

            const parsedResume = {
                title: file.name,
                theme: "classic",
                content: {
                    name: parsedName,
                    email: parsedEmail,
                    phone: "+1 (555) 012-3456",
                    github: "https://github.com/alexsmith",
                    experienceRole: parsedRole,
                    experienceDesc: parsedExpDesc,
                    projectTitle: parsedProjTitle,
                    projectDesc: parsedProjDesc
                },
                analysis_feedback: analysisData
            };
            
            // Save in localStorage
            localStorage.setItem("campusmate_sandbox_resume", JSON.stringify(parsedResume));
            localStorage.setItem("campusmate_sandbox_resumescore", 78);
            localStorage.setItem("campusmate_sandbox_resume_feedback", JSON.stringify(analysisData));
            
            response = {
                success: true,
                filename: file.name,
                atsScore: 78,
                readabilityScore: 85,
                industryMatchScore: 72,
                feedback: analysisData
            };

            currentUser.xp += 50;
            localStorage.setItem("campusmate_sandbox_user", JSON.stringify(currentUser));
        } else {
            response = await API.uploadResumeFile(file);
        }

        // Fill out inputs
        statusText.innerHTML = `<span class="text-green"><i class="fa-solid fa-circle-check"></i> "${file.name}" uploaded & parsed successfully!</span>`;
        
        // Reload resume view
        loadResumeView();
        // Load dashboard stats
        loadDashboard();
        
        alert(`Resume uploaded successfully! ATS Score: ${response.atsScore}%`);
    } catch (e) {
        console.error(e);
        statusText.innerHTML = `<span class="text-red"><i class="fa-solid fa-circle-xmark"></i> Failed to parse file: ${e.message}</span>`;
    }
}
