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
    
    // Pre-fill Gemini Key if saved
    const savedKey = localStorage.getItem("campusmate_gemini_key");
    const keyInput = document.getElementById("sidebar-gemini-key");
    if (savedKey && keyInput) {
        keyInput.value = savedKey;
    }
    
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
    resetAuthPasswords();
}

function switchAuthTab(tab) {
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");
    const loginTabBtn = document.getElementById("tab-login-btn");
    const signupTabBtn = document.getElementById("tab-signup-btn");
    const errorMsg = document.getElementById("auth-error-msg");

    errorMsg.classList.add("hidden");
    resetAuthPasswords();

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

function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector("i");
    if (input.type === "password") {
        input.type = "text";
        icon.className = "fa-solid fa-eye-slash";
    } else {
        input.type = "password";
        icon.className = "fa-solid fa-eye";
    }
}

function resetAuthPasswords() {
    const ids = ["login-password", "signup-password"];
    ids.forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.type = "password";
            const container = input.parentElement;
            if (container) {
                const btn = container.querySelector(".password-toggle-btn");
                if (btn && btn.querySelector("i")) {
                    btn.querySelector("i").className = "fa-solid fa-eye";
                }
            }
        }
    });
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
    
    // Ensure sandbox nodes are seeded with the full 25 milestones
    let sandboxNodes = localStorage.getItem("campusmate_sandbox_nodes");
    let needsReseed = false;
    if (!sandboxNodes) {
        needsReseed = true;
    } else {
        try {
            const parsed = JSON.parse(sandboxNodes);
            if (!Array.isArray(parsed) || parsed.length < 25) {
                needsReseed = true;
            }
        } catch (e) {
            needsReseed = true;
        }
    }
    if (needsReseed) {
        seedSandboxRoadmap(currentUser.targetRole || "Full-Stack Dev");
    }
    
    // Show sandbox UI indicators
    document.getElementById("sandbox-badge").classList.remove("hidden");
    
    // Transition layouts
    document.getElementById("landing-container").classList.add("hidden");
    closeAuthModal();
    showMainApp();
    loadDashboard();
}

function getPredefinedRoadmapJS(role) {
    const roleLower = role.toLowerCase();
    let milestones = [];
    let provider = "FreeCodeCamp / OpenJS";
    let cert = "Meta Front-End Developer Professional Certificate";
    
    if (roleLower.includes("cyber") || roleLower.includes("security")) {
        milestones = [
            ["Networking & OSI Model Essentials", "Master TCP/IP, subnets, DNS, and OSI layer fundamentals."],
            ["IP Subnetting & Packet Routing", "Learn how routers direct packets across subnets and local area networks."],
            ["Common Protocols & Audits", "Examine and audit DNS, HTTP, SSH, FTP, and DHCP protocols."],
            ["Command Line & Bash Scripting", "Master Linux file navigation, permissions, and automation scripts."],
            ["Windows Security & PowerShell", "Learn Windows active directory administration and powershell commands."],
            ["Intro to Cryptography & Keys", "Differentiate symmetric vs asymmetric encryption and key exchange."],
            ["Hashing & Integrity Verification", "Use SHA, MD5, and digital signatures to audit document integrity."],
            ["Reconnaissance & Nmap Scanning", "Scan open ports, discover OS versions, and catalog target assets."],
            ["Packet Sniffing with Wireshark", "Capture and analyze network frames to trace protocol payloads."],
            ["Firewall ACLs & Segmentation", "Configure network security groups and block unauthorized port access."],
            ["SSH Hardening & Security Audits", "Audit SSH configuration, disable root login, and enforce key auth."],
            ["Identity Access Management (IAM)", "Configure multi-factor auth, role bindings, and credential policies."],
            ["OWASP Top 10 Security Risks", "Understand SQL injection, XSS, and broken access controls."],
            ["SQL Injection & Defensive Coding", "Exploit SQL weaknesses and implement parameterized query overrides."],
            ["Metasploit Framework Exploitation", "Configure exploit modules, payloads, and establish shell listeners."],
            ["Wireless WPA2/WPA3 Security", "Learn security handshakes, packet capture, and deauth attacks."],
            ["IDS/IPS Snort Rules Configuration", "Create snort signatures to flag and block network attack profiles."],
            ["SIEM Log Auditing with Splunk", "Index server logs and create alerts for suspicious login behaviors."],
            ["Threat Hunting & Log Correlation", "Correlate syslog and auth logs to map persistent attack paths."],
            ["Malware Analysis: Static Review", "Analyze PE headers, string hashes, and import tables of binaries."],
            ["Malware Analysis: Dynamic Scans", "Run binaries in a secure sandbox and monitor registry changes."],
            ["Cloud Shared Responsibility Models", "Audit AWS and Azure security frameworks and identity bindings."],
            ["Cloud Gateways & WAF Security", "Deploy web application firewalls and lock down virtual networks."],
            ["Penetration Testing Scope & Ethics", "Learn scopes of work, reporting standards, and legal compliance."],
            ["Purple Teaming & Incident Response", "Collaborate on attack/defense simulations and incident reporting."]
        ];
        provider = "CompTIA / EC-Council";
        cert = "CompTIA Security+";
    } else if (roleLower.includes("ai engineering") || roleLower.includes("ai engineer")) {
        milestones = [
            ["Python Programming & Tool Setup", "Install dependencies, write syntax commands, and configure VS Code."],
            ["Control Flow & Logic in Python", "Write conditionals, loops, and conditional flow logic statements."],
            ["Functions & Modular File Structures", "Create modular python functions, scripts, and exception boundaries."],
            ["OOP Principles & Custom Classes", "Use classes, inheritance, and object abstractions in Python."],
            ["File Parsing: JSON, CSV, & Files", "Read local log files and clean structured telemetry inputs."],
            ["NumPy Vectorized Array Workflows", "Create matrices, compute dot products, and optimize loops."],
            ["Pandas DataFrames & Aggregations", "Load tabular data, group stats, and index complex datasets."],
            ["Data Visualization with Seaborn", "Plot correlation heatmaps, line charts, and bar diagrams."],
            ["Linear Algebra for Model Weights", "Compute matrix determinants, eigenvalues, and dot multiplications."],
            ["Gradient Descent Optimizations", "Learn loss functions, derivatives, and learning rates."],
            ["Probability Foundations for Models", "Calculate Bayes theorem probabilities and normal distributions."],
            ["Supervised Learning Regression Models", "Train linear regression models using Scikit-Learn."],
            ["Decision Trees & Ensemble Forests", "Train classifier models and verify split indices."],
            ["Support Vector Classification", "Configure hyperplanes and kernel transformations."],
            ["Unsupervised Clustering Algorithms", "Group data rows using K-Means and DBSCAN algorithms."],
            ["Dimensionality Reduction with PCA", "Condense feature columns while preserving data variance."],
            ["ROC, AUC & F1-Score Evaluations", "Construct confusion matrices and optimize threshold curves."],
            ["Introduction to PyTorch Tensors", "Setup tensor structures, auto-differentiation, and backpropagation."],
            ["Convolutional Image Neural Networks", "Construct CNN layers for computer vision digit classifications."],
            ["RNNs & LSTMs for Time-Series", "Train sequential networks to predict stock trends or logs."],
            ["NLP Tokenization & Embeddings", "Convert text inputs to vector tokens and bag-of-words."],
            ["Transformer Encoder-Decoder Layers", "Learn self-attention mechanisms and query-key-value vectors."],
            ["Prompt Engineering & System Prompts", "Create system instructions for LLM completions."],
            ["RAG Pipelines & Vector Databases", "Retrieve local PDF text chunks and search ChromaDB vectors."],
            ["Exposing Models via FastAPI Docker", "Wrap model inference scripts inside FastAPI and run via Docker."]
        ];
        provider = "Microsoft / Google";
        cert = "Azure AI Engineer Associate";
    } else if (roleLower.includes("machine") || roleLower.includes("ml")) {
        milestones = [
            ["Python Setup & Jupyter Notebooks", "Configure environments, install pip packages, and write cells."],
            ["Variables, Lists & Loops in Python", "Work with python sequences, slicing, and dictionaries."],
            ["Functions, Errors & Imports", "Define custom methods, raise exceptions, and load modules."],
            ["NumPy Arrays & Linear Algebra", "Execute matrix arithmetic, reshape tensors, and select slices."],
            ["Pandas Data Analytics Essentials", "Filter rows, map column values, and handle NaN placeholders."],
            ["Data Visualization & Distributions", "Construct histograms, scatter plots, and box plots."],
            ["Linear & Polynomial Regressions", "Perform curve fitting and compute mean squared error metrics."],
            ["Logistic Regression & Binary Targets", "Train sigmoid models to classify user churn anomalies."],
            ["Decision Trees & Hyperparameters", "Prune tree nodes, configure min_samples, and plot rules."],
            ["Random Forests & Bagging Methods", "Combine tree predictors and inspect feature importances."],
            ["Support Vector Machines & Kernels", "Configure radial basis functions and margin soft parameters."],
            ["K-Means Clustering & Elbow Curves", "Segment user segments and compute inertia scores."],
            ["Principal Component Analysis (PCA)", "Reduce dimensions and analyze explained variance ratios."],
            ["Overfitting & Cross-Validation", "Run K-Fold validations and diagnose train/test curves."],
            ["Stochastic Gradient Descent (SGD)", "Optimize loss parameters using mini-batches."],
            ["PyTorch Neural Networks Basics", "Define linear layers, activation functions, and optimizer hooks."],
            ["Training Custom CNN Model Layers", "Build convolution and pooling loops for image inputs."],
            ["LSTMs & Text Generation loops", "Setup sequence-to-sequence neural architectures."],
            ["Feature Engineering & Scaling", "Apply StandardScalers, one-hot encoders, and log fixes."],
            ["Model Serialization & Joblib", "Export weights files and write fast loading hooks."],
            ["FastAPI Inference Controllers", "Deploy a backend route that loads model weights and classifies."],
            ["Dockerizing ML Service Environs", "Build clean container layers containing model assets."],
            ["Deploying ML models to Cloud VM", "Run inference containers on cloud servers behind proxy gates."],
            ["Monitoring Model Drift telemetry", "Setup dashboard tracking for live prediction confidence graphs."],
            ["Advanced Hyperparameter Search", "Run Optuna, grid searches, and optimize batch size metrics."]
        ];
        provider = "Google Cloud / AWS";
        cert = "GCP Professional Machine Learning Engineer";
    } else if (roleLower.includes("data science") || roleLower.includes("data scientist")) {
        milestones = [
            ["Python & Jupyter Basics", "Configure notebooks, install pandas/matplotlib, and write scripts."],
            ["Pandas: Loading & Selecting Data", "Read CSV/JSON files, inspect head, and select columns."],
            ["Pandas: Data Cleaning Strategies", "Drop duplicate rows, fill missing cells, and change types."],
            ["Exploratory Data Analysis (EDA)", "Create correlation heatmaps and identify data anomalies."],
            ["Matplotlib & Seaborn Custom Plots", "Customize chart colors, labels, axes, and legends."],
            ["SQL: Querying Databases for Analysis", "Write SELECT statements, filter conditions, and limits."],
            ["SQL: Joins, Groups & Aggregations", "Combine tables using INNER/LEFT JOIN and count metrics."],
            ["Descriptive Statistics Foundations", "Calculate mean, median, mode, variance, and standard deviation."],
            ["Probability Distributions & Z-Scores", "Analyze normal distributions, outliers, and normalize scales."],
            ["Hypothesis Testing & T-Tests", "Set null hypotheses, calculate p-values, and check significance."],
            ["A/B Testing Experiments Design", "Determine sample sizes, control groups, and verify conversions."],
            ["Linear Regression & Correlation", "Assess Pearson correlation and fit regression lines."],
            ["Logistic Regression Classifications", "Predict binary classifications and plot confusion matrices."],
            ["Decision Trees for Analytics", "Create rule trees and print feature importance lists."],
            ["Time Series Analysis & Forecasting", "Decompose trends, seasonal cycles, and run ARIMA models."],
            ["Text Mining & Basic NLP Analysis", "Clean text strings, remove stopwords, and build wordclouds."],
            ["Dimensionality Reduction & Clustering", "Run PCA and group customer behavior using K-Means."],
            ["Feature Selection Techniques", "Filter features using ANOVA, chi-square, and mutual info."],
            ["Data Pipelines: ETL Essentials", "Extract raw files, transform schema mappings, and save to SQL."],
            ["Intro to Big Data & Spark DataFrames", "Run distributed queries on large datasets using PySpark."],
            ["BI Tools: Building Dashboard Mockups", "Design visual tracking widgets for business managers."],
            ["Deploying Analytical Reports as APIs", "Expose key stats, summaries, and predictions via FastAPI."],
            ["Dockerizing ETL Script Containers", "Containerize data import scripts to run on daily schedules."],
            ["Cloud Data Warehouse Foundations", "Learn query configurations for AWS Redshift or Google BigQuery."],
            ["Capstone: Interactive Data Dashboard", "Deliver a comprehensive project featuring clean ETL and plots."]
        ];
        provider = "Microsoft / Databricks";
        cert = "Microsoft Certified: Power BI Data Analyst Associate";
    } else if (roleLower.includes("cloud")) {
        milestones = [
            ["Cloud Computing Fundamentals", "Learn IaaS, PaaS, SaaS, and public vs private structures."],
            ["Virtual Machines & OS Provisioning", "Spin up VMs, configure SSH access, and update repositories."],
            ["Virtual Networking & Subnetting", "Deploy virtual networks, design subnets, and configure routes."],
            ["Firewalls & Network Access Control", "Configure ingress/egress rules and block open SSH ports."],
            ["Cloud Object Storage Essentials", "Create storage buckets, configure access controls, and files."],
            ["IAM: Users, Groups & Policy JSON", "Write strict access policies and delegate privileges safely."],
            ["SQL Databases in the Cloud", "Provision relational instances and audit connectivity links."],
            ["NoSQL Cloud Database Engines", "Setup key-value engines and configure primary partition keys."],
            ["Load Balancers & High Availability", "Distribute HTTP requests across target server pools."],
            ["Auto-Scaling & Elastic Operations", "Configure rules to automatically scale node counts on load."],
            ["Serverless Functions (FaaS)", "Deploy event-driven functions and configure trigger endpoints."],
            ["DNS Routing & Domain Registries", "Configure target routes, health checks, and domain maps."],
            ["Content Delivery Networks (CDN)", "Cache static images and CSS stylesheets at edge locations."],
            ["Monitoring, Metrics & Logs Tracker", "Setup metric graphs and track CPU/memory alerts."],
            ["Backup, Restore & Disaster Recovery", "Schedule snapshot policies and test database recovery loops."],
            ["Terraform: Infrastructure as Code (IaC)", "Define VMs, networks, and firewalls using YAML/HCL configurations."],
            ["Terraform: State Files & Variables", "Manage state configs, output parameters, and modules."],
            ["Cloud Container Registry setups", "Build Docker images and push to cloud registry stores."],
            ["Kubernetes Cloud Clusters (EKS/AKS)", "Provision managed Kubernetes clusters and connect kubectl."],
            ["Hybrid Cloud & VPN Tunnel Gateway", "Bridge local data networks to cloud nodes using secure VPNs."],
            ["Cloud Billing & Cost Controls", "Set spending limits, configure alarms, and clean unused disks."],
            ["Shared Responsibility Security Audits", "Evaluate vulnerability logs, WAF alerts, and security groups."],
            ["Automated VM Configuration (Ansible)", "Write playbooks to deploy web servers on fresh cloud VMs."],
            ["Server Migration Strategies", "Learn how to lift and shift database nodes to cloud instances."],
            ["Capstone: Deploy Secure Cloud Cluster", "Deploy a complete SaaS network behind load balancers with WAF."]
        ];
        provider = "Amazon AWS / Microsoft";
        cert = "AWS Certified Solutions Architect – Associate";
    } else if (roleLower.includes("devops")) {
        milestones = [
            ["DevOps Culture & Linux Shell Power", "Learn standard commands, file management, and terminal tools."],
            ["Git Foundations & Branching Models", "Master merging, rebasing, pull requests, and git-flow patterns."],
            ["Bash Scripting & Automation Loops", "Write automation scripts to clean temp files and parse logs."],
            ["Docker: Building Custom Containers", "Write Dockerfiles, configure layers, and run entrypoints."],
            ["Docker Compose: Multi-Container Setup", "Run backend APIs and database nodes side-by-side using YAML."],
            ["Docker Volumes & Persistent Storage", "Configure mount volumes and preserve data across restarts."],
            ["CI/CD: GitHub Actions Workflows", "Create YAML workflows to compile code on push events."],
            ["CI/CD: Automated Linter & Unit Tests", "Integrate automated check steps and block broken pull builds."],
            ["Infrastructure as Code (IaC) Basics", "Learn declarative config models and write simple YAML plans."],
            ["Terraform: Provisioning Local Dev Host", "Write terraform configs to deploy Docker containers."],
            ["Terraform: State Management & Backends", "Configure remote state locking to avoid resource conflicts."],
            ["Configuration Management: Ansible", "Write playbooks to configure packages on server networks."],
            ["Continuous Deployment: SSH Web Deploy", "Auto-deploy code directly to remote servers using SSH scripts."],
            ["Monitoring Systems: Prometheus Basics", "Expose metrics endpoints and monitor CPU/RAM utilization."],
            ["Log Aggregation: ELK Stack / Grafana", "Collect application logs, construct dashboards, and monitor errors."],
            ["Kubernetes: Pods, Services & Deployments", "Write YAML manifests to deploy container sets locally."),
            ["Kubernetes: ConfigMaps & Secrets", "Inject environment variables and secret tokens securely."],
            ["Kubernetes: Ingress & Domain Routing", "Deploy ingress controllers to route HTTP traffic to services."],
            ["Helm: Packaging Kubernetes Apps", "Use Helm charts to install persistent database clusters."],
            ["GitOps: Intro to ArgoCD pipelines", "Sync Kubernetes clusters directly with git repository state."],
            ["SaaS Logging & Alerting Triggers", "Setup Slack/email alert webhooks for down server nodes."],
            ["CI/CD: Artifact Registries & Packages", "Publish compiled images to secure image registries."],
            ["Security: Scanning Docker Images (Trivy)", "Integrate CVE vulnerability scans inside build jobs."],
            ["DevSecOps: Secret Key Scanning", "Audit repository histories and block commit keys from git."],
            ["Capstone: Zero-Downtime CD Pipeline", "Deliver an automated pipeline that builds, tests, and rolls updates."]
        ];
        provider = "HashiCorp / RedHat";
        cert = "HashiCorp Certified: Terraform Associate";
    } else if (roleLower.includes("full") || roleLower.includes("web") || roleLower.includes("developer") || roleLower.includes("engineering") || roleLower.includes("software")) {
        milestones = [
            ["Internet Basics & Web Architectures", "Understand HTTP protocols, DNS servers, and request lifecycles."],
            ["Semantic HTML5 Document Design", "Learn layout structures, inputs, buttons, and document trees."],
            ["CSS3 Styling: Flexbox & Page Grids", "Align interface cards, configure grid spans, and margins."],
            ["Responsive CSS Variables & Queries", "Build responsive layouts using variables and media queries."],
            ["Modern Styling: Brutalist & Glassmorphism", "Apply neo-brutalist solid black borders and glass cards."],
            ["JavaScript Variables, Arrays & loops", "Master basic data handling, loops, and conditions."],
            ["DOM Manipulation & Page Events", "Write event listeners to dynamically modify page elements."],
            ["JavaScript Promises & Async/Await", "Fetch JSON payloads from backend endpoints asynchronously."],
            ["React: Creating Functional Components", "Learn components, props, and render layouts in React."],
            ["React: Hooks, State & Input Binding", "Use useState and useEffect to bind input variables."],
            ["React: Context API & Routing", "Configure app navigation tabs and global user states."],
            ["Node.js Runtime & Package Systems", "Write terminal scripts and load external modules."],
            ["Express.js REST APIs & Routing", "Configure GET/POST routes and handle JSON body payloads."],
            ["Relational Database Schema Design", "Design PostgreSQL tables, keys, and relational maps."],
            ["SQL Queries, Indexing & Joins", "Write query commands, join tables, and index query fields."],
            ["ORM integration: SQLModel / Prisma", "Map database tables to programming models."],
            ["Authentication: JWT Tokens & Hash", "Hash passwords with bcrypt and sign JWT session tokens."],
            ["API Gateways, CORS & Rate Limiting", "Secure endpoints from unauthorized cross-origin requests."],
            ["Unit Testing Backend Controllers", "Write test suites, run assertions, and mock databases."],
            ["Frontend Integration & Fetch Client", "Call authentication and data endpoints from frontend pages."],
            ["Dockerizing Full Stack Applications", "Containerize frontend and backend layers into single images."],
            ["CI/CD Pipelines: Automated Release", "Configure GitHub Actions to compile and deploy to cloud hosts."],
            ["Performance: Query Caching with Redis", "Cache slow database outputs and speed up response cycles."],
            ["Real-Time Communication: WebSockets", "Build live interactive chat hubs using WebSocket listeners."],
            ["Capstone: Deploy E-Commerce Platform", "Deploy a complete app containing user auth, items, and billing."]
        ];
        provider = "FreeCodeCamp / OpenJS";
        cert = "Meta Front-End Developer Professional Certificate";
    } else {
        milestones = [
            ["Mobile Ecosystems: iOS & Android", "Learn native app files, lifecycle stages, and app store rules."],
            ["Command Line Tools & Mobile SDKs", "Configure Android Studio, Xcode, simulator systems, and paths."],
            ["Dart / Kotlin Language Foundations", "Master variables, loops, classes, and types of native languages."],
            ["Functions & Modular File Imports", "Create reusable files, helper scripts, and async modules."],
            ["UI Layout: Widgets & Layout Grids", "Deploy layout cards, flex lists, columns, and margins."],
            ["Mobile Styling, Themes & Colors", "Apply light/dark mode support, responsive fonts, and buttons."],
            ["State Management: Local Page States", "Track text inputs, form selections, and local toggle variables."],
            ["Handling User Events: Gestures & Inputs", "Capture taps, swipes, long presses, and input focus changes."],
            ["HTTP API Integration: Networking", "Fetch data from REST APIs, decode JSON, and handle connection errors."],
            ["Local Database Storage (SQLite/Hive)", "Persist user settings and catalog local records offline."],
            ["Mobile Authentication: JWT & OAuth", "Securely store login tokens and manage user sessions."],
            ["Navigation Architectures: Tab Routers", "Configure stack navigation, tab bars, and back buttons."],
            ["Camera, Files & Device Permissions", "Request access to camera features and load local photos."],
            ["Location Services & Map Rendering", "Fetch GPS coordinates and render locations on map widgets."],
            ["Push Notifications & Background Jobs", "Setup notification triggers and sync data in the background."],
            ["Responsive UI for Mobile & Tablets", "Scale padding, layouts, and image assets dynamically."],
            ["Global State Management (Bloc/Redux)", "Share user profiles and roadmaps across different screens."],
            ["Unit & Widget UI Testing", "Write assertions for widget render states and test logic blocks."],
            ["CI/CD: Building Release Bundles", "Auto-compile APK/IPA builds and run checks using CLI tools."],
            ["App Optimizations: Caching & Loading", "Optimize image download sizes and cache local JSON records."],
            ["Google Play & Apple Store Deployment", "Publish production builds to developer testing tracks."],
            ["Error Logging & Crashlytics", "Integrate crash detectors and monitor runtime stack traces."],
            ["Animations: Transitions & Micro-actions", "Add page transitions and micro-interactions for items."],
            ["Securing App Files & Keystore Storage", "Encrypt API key tokens and secure password files in keychains."],
            ["Capstone Mobile App Deployment", "Deploy a fully functional React Native/Flutter app containing auth and maps."]
        ];
        provider = "Google / Apple";
        cert = "Google Associate Android Developer";
    }
    
    return milestones.map((m, i) => {
        const diff = i < 8 ? "BEGINNER" : (i < 17 ? "INTERMEDIATE" : "ADVANCED");
        const dur = `${8 + (i % 5)*2} hours`;
        return {
            id: `node-${i+1}`,
            title: `Step ${i+1}: ${m[0]}`,
            description: m[1],
            difficulty: diff,
            estimated_duration: dur,
            resources: [{title: `Official documentation for ${m[0]}`, url: "https://learn.microsoft.com"}],
            projects: [{title: `Implementation Project - Step ${i+1}`, description: `Build a practical system that demonstrates deep knowledge of ${m[0]}.`, tasks: ["Configure the framework settings", "Write code files implementation", "Verify local test suits passes"]}],
            certifications: [{name: cert, provider: provider}],
            status: i === 0 ? "AVAILABLE" : "LOCKED"
        };
    });
}

function seedSandboxRoadmap(role) {
    const nodes = getPredefinedRoadmapJS(role);
    
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

    const sidebar = document.querySelector(".sidebar");
    if (sidebar && sidebar.classList.contains("open")) {
        sidebar.classList.remove("open");
        const backdrop = document.getElementById("sidebar-backdrop");
        if (backdrop) backdrop.style.display = "none";
    }

    document.querySelectorAll(".mobile-nav-item").forEach(item => {
        if (item.getAttribute("data-mobile-tab") === tabName) {
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

    // Scroll workspace back to top on tab switch
    const workspaceEl = document.querySelector(".workspace");
    if (workspaceEl) {
        workspaceEl.scrollTop = 0;
    }
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
            const resumeFeedback = JSON.parse(localStorage.getItem("campusmate_sandbox_resume_feedback") || "null");
            
            let readabilityScore = 0;
            let industryMatchScore = 0;
            if (resumeFeedback) {
                readabilityScore = 85;
                industryMatchScore = 72;
                if (parseInt(resumeScore) >= 90) {
                    readabilityScore = 95;
                    industryMatchScore = 90;
                }
            }
            
            const completedCount = nodes.filter(n => n.status === "COMPLETED").length;
            const progress = nodes.length > 0 ? Math.round((completedCount / nodes.length) * 100) : 0;
            const nextNode = nodes.find(n => n.status === "AVAILABLE" || n.status === "IN_PROGRESS");
            
            let certsCount = 0;
            nodes.forEach(n => {
                if (n.status !== "COMPLETED" && n.certifications) {
                    certsCount += n.certifications.length;
                }
            });
            
            stats = {
                fullName: currentUser.fullName,
                streak: currentUser.streak,
                xp: currentUser.xp,
                targetRole: roadmapInfo ? roadmapInfo.targetRole : null,
                roadmapProgress: progress,
                nextNode: nextNode ? nextNode.title : "Generate a roadmap first!",
                resumeScore: parseInt(resumeScore),
                readabilityScore: readabilityScore,
                industryMatchScore: industryMatchScore,
                certsCount: certsCount,
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
        
        const readWidget = document.getElementById("dashboard-readability-score");
        if (readWidget) readWidget.innerText = `${stats.readabilityScore || 0}%`;
        const readBar = document.getElementById("dashboard-readability-bar");
        if (readBar) readBar.style.width = `${stats.readabilityScore || 0}%`;

        const indWidget = document.getElementById("dashboard-industry-score");
        if (indWidget) indWidget.innerText = `${stats.industryMatchScore || 0}%`;
        const indBar = document.getElementById("dashboard-industry-bar");
        if (indBar) indBar.style.width = `${stats.industryMatchScore || 0}%`;

        const certsWidget = document.getElementById("dashboard-certs-count");
        if (certsWidget) certsWidget.innerText = stats.certsCount || 0;

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
// --- RESUME BUILDER FUNCTIONS ---
let currentDraftId = "draft-1";
let activeBulletInput = null;

// Track active bullet input for verb assistant injection
document.addEventListener("focusin", (e) => {
    if (e.target && e.target.classList && e.target.classList.contains("res-bullet-input")) {
        activeBulletInput = e.target;
    }
});

function insertActionVerb(verb) {
    if (!activeBulletInput) {
        activeBulletInput = document.getElementById("res-exp-b1");
    }
    if (!activeBulletInput) return;
    
    const val = activeBulletInput.value.trim();
    if (val === "") {
        activeBulletInput.value = verb + " ";
    } else {
        activeBulletInput.value = verb + " " + activeBulletInput.value;
    }
    syncResumeFields();
    activeBulletInput.focus();
}

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

        initLiveKeywords();

        if (resume) {
            document.getElementById("resume-title-field").value = resume.title;
            document.getElementById("resume-theme-select").value = resume.theme || "classic";
            
            populateResumeForm(resume.content);
            
            changeResumeTheme();
            syncResumeFields();
            
            if (resume.analysis_feedback) {
                renderATSFeedback(resume.analysis_feedback);
            }
        } else {
            resetResumeFormToDefault(currentDraftId);
            changeResumeTheme();
            syncResumeFields();
        }
    } catch (e) {
        console.error("Failed to load resume", e);
    }
}

function syncResumeFields() {
    const syncText = (id, renderId, prefix = "", suffix = "") => {
        const input = document.getElementById(id);
        const render = document.getElementById(renderId);
        if (input && render) {
            render.innerText = input.value ? (prefix + input.value + suffix) : "";
        }
    };

    // Personal Details
    syncText("res-name", "res-render-name");
    syncText("res-address", "res-render-address");
    syncText("res-email", "res-render-email");
    syncText("res-phone", "res-render-phone");
    syncText("res-linkedin", "res-render-linkedin");
    syncText("res-github", "res-render-links");

    // Education 1
    syncText("res-edu1-inst", "res-render-edu1-inst");
    syncText("res-edu1-degree", "res-render-edu1-degree");
    syncText("res-edu1-dates", "res-render-edu1-dates");
    syncText("res-edu1-gpa", "res-render-edu1-gpa");
    syncText("res-edu1-coursework", "res-render-edu1-coursework", "Relevant Coursework: ");

    // Education 2
    syncText("res-edu2-inst", "res-render-edu2-inst");
    syncText("res-edu2-degree", "res-render-edu2-degree");
    syncText("res-edu2-dates", "res-render-edu2-dates");
    syncText("res-edu2-gpa", "res-render-edu2-gpa");

    // Technical Skills
    syncText("res-skills-prog", "res-render-skills-prog");
    syncText("res-skills-cyber", "res-render-skills-cyber");
    syncText("res-skills-os", "res-render-skills-os");
    syncText("res-skills-tools", "res-render-skills-tools");
    syncText("res-skills-web", "res-render-skills-web");

    // Experience
    syncText("res-exp-role", "res-render-exp-role");
    syncText("res-exp-comp", "res-render-exp-comp");
    syncText("res-exp-dates", "res-render-exp-dates");
    syncText("res-exp-b1", "res-render-exp-b1");
    syncText("res-exp-b2", "res-render-exp-b2");
    syncText("res-exp-b3", "res-render-exp-b3");
    syncText("res-exp-b4", "res-render-exp-b4");

    // Projects
    syncText("res-proj-title", "res-render-proj-title");
    syncText("res-proj-link", "res-render-proj-link");
    syncText("res-proj-b1", "res-render-proj-b1");
    syncText("res-proj-b2", "res-render-proj-b2");
    syncText("res-proj-b3", "res-render-proj-b3");

    // Certifications
    syncText("res-cert-c1", "res-render-cert-c1");
    syncText("res-cert-c2", "res-render-cert-c2");
    syncText("res-cert-c3", "res-render-cert-c3");
    syncText("res-cert-c4", "res-render-cert-c4");

    runLiveKeywordScan();
}

// Bind live changes to sync function
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".resume-fields-panel input, .resume-fields-panel textarea").forEach(el => {
        el.addEventListener("input", syncResumeFields);
    });
});

function changeResumeTheme() {
    const theme = document.getElementById("resume-theme-select").value;
    const paper = document.getElementById("resume-sheet-paper");
    if (paper) {
        paper.className = `resume-sheet ${theme}`;
    }
}

async function saveResumeContent() {
    const title = document.getElementById("resume-title-field").value;
    const theme = document.getElementById("resume-theme-select").value;
    
    const content = getResumeFormContent();
    const origText = document.getElementById("ats-original-score").innerText;
    const upgText = document.getElementById("ats-upgraded-score").innerText;
    
    content.originalScore = origText.replace("%", "");
    content.upgradedScore = upgText.replace("%", "");

    try {
        if (appMode === "sandbox") {
            const resumeObj = {
                title,
                theme,
                content,
                analysis_feedback: JSON.parse(localStorage.getItem("campusmate_sandbox_resume_feedback") || "null")
            };
            localStorage.setItem("campusmate_sandbox_resume", JSON.stringify(resumeObj));
            
            // Save to draft slot
            const drafts = JSON.parse(localStorage.getItem("campusmate_sandbox_drafts") || "{}");
            drafts[currentDraftId] = { title, theme, content };
            localStorage.setItem("campusmate_sandbox_drafts", JSON.stringify(drafts));
            
            alert("Sandbox resume draft saved locally!");
        } else {
            await API.saveResume(title, theme, content);
            
            // Save to draft slot
            const storageKey = `campusmate_drafts_${currentUser.email || "user"}`;
            const drafts = JSON.parse(localStorage.getItem(storageKey) || "{}");
            drafts[currentDraftId] = { title, theme, content };
            localStorage.setItem(storageKey, JSON.stringify(drafts));
            
            alert("Resume draft saved successfully!");
        }
    } catch (e) {
        alert("Failed to save resume: " + e.message);
    }
}

// --- DRAFT VERSION MANAGEMENT ---
function handleDraftSelection() {
    saveCurrentDraftData();
    currentDraftId = document.getElementById("resume-draft-select").value;
    loadDraftData(currentDraftId);
}

function saveCurrentDraftData() {
    const title = document.getElementById("resume-title-field").value;
    const theme = document.getElementById("resume-theme-select").value;
    const content = getResumeFormContent();
    const origText = document.getElementById("ats-original-score").innerText;
    const upgText = document.getElementById("ats-upgraded-score").innerText;
    
    content.originalScore = origText.replace("%", "");
    content.upgradedScore = upgText.replace("%", "");

    if (appMode === "sandbox") {
        const drafts = JSON.parse(localStorage.getItem("campusmate_sandbox_drafts") || "{}");
        drafts[currentDraftId] = { title, theme, content };
        localStorage.setItem("campusmate_sandbox_drafts", JSON.stringify(drafts));
    } else {
        const storageKey = `campusmate_drafts_${currentUser.email || "user"}`;
        const drafts = JSON.parse(localStorage.getItem(storageKey) || "{}");
        drafts[currentDraftId] = { title, theme, content };
        localStorage.setItem(storageKey, JSON.stringify(drafts));
    }
}

function loadDraftData(draftId) {
    let draft = null;
    if (appMode === "sandbox") {
        const drafts = JSON.parse(localStorage.getItem("campusmate_sandbox_drafts") || "{}");
        draft = drafts[draftId];
    } else {
        const storageKey = `campusmate_drafts_${currentUser.email || "user"}`;
        const drafts = JSON.parse(localStorage.getItem(storageKey) || "{}");
        draft = drafts[draftId];
    }

    if (draft) {
        document.getElementById("resume-title-field").value = draft.title || "Guest Resume Draft";
        document.getElementById("resume-theme-select").value = draft.theme || "classic";
        populateResumeForm(draft.content);
    } else {
        resetResumeFormToDefault(draftId);
    }
    changeResumeTheme();
    syncResumeFields();
}

function getResumeFormContent() {
    return {
        name: document.getElementById("res-name").value,
        address: document.getElementById("res-address").value,
        email: document.getElementById("res-email").value,
        phone: document.getElementById("res-phone").value,
        linkedin: document.getElementById("res-linkedin").value,
        github: document.getElementById("res-github").value,
        
        edu1Inst: document.getElementById("res-edu1-inst").value,
        edu1Degree: document.getElementById("res-edu1-degree").value,
        edu1Dates: document.getElementById("res-edu1-dates").value,
        edu1Gpa: document.getElementById("res-edu1-gpa").value,
        edu1Coursework: document.getElementById("res-edu1-coursework").value,
        
        edu2Inst: document.getElementById("res-edu2-inst").value,
        edu2Degree: document.getElementById("res-edu2-degree").value,
        edu2Dates: document.getElementById("res-edu2-dates").value,
        edu2Gpa: document.getElementById("res-edu2-gpa").value,
        
        skillsProg: document.getElementById("res-skills-prog").value,
        skillsCyber: document.getElementById("res-skills-cyber").value,
        skillsOs: document.getElementById("res-skills-os").value,
        skillsTools: document.getElementById("res-skills-tools").value,
        skillsWeb: document.getElementById("res-skills-web").value,
        
        experienceRole: document.getElementById("res-exp-role").value,
        experienceComp: document.getElementById("res-exp-comp").value,
        experienceDates: document.getElementById("res-exp-dates").value,
        experienceB1: document.getElementById("res-exp-b1").value,
        experienceB2: document.getElementById("res-exp-b2").value,
        experienceB3: document.getElementById("res-exp-b3").value,
        experienceB4: document.getElementById("res-exp-b4").value,
        
        projectTitle: document.getElementById("res-proj-title").value,
        projectLink: document.getElementById("res-proj-link").value,
        projectB1: document.getElementById("res-proj-b1").value,
        projectB2: document.getElementById("res-proj-b2").value,
        projectB3: document.getElementById("res-proj-b3").value,
        
        certC1: document.getElementById("res-cert-c1").value,
        certC2: document.getElementById("res-cert-c2").value,
        certC3: document.getElementById("res-cert-c3").value,
        certC4: document.getElementById("res-cert-c4").value
    };
}

function populateResumeForm(c) {
    if (!c) return;
    if (c.name !== undefined) document.getElementById("res-name").value = c.name;
    if (c.address !== undefined) document.getElementById("res-address").value = c.address;
    if (c.email !== undefined) document.getElementById("res-email").value = c.email;
    if (c.phone !== undefined) document.getElementById("res-phone").value = c.phone;
    if (c.linkedin !== undefined) document.getElementById("res-linkedin").value = c.linkedin;
    if (c.github !== undefined) document.getElementById("res-github").value = c.github;
    
    if (c.edu1Inst !== undefined) document.getElementById("res-edu1-inst").value = c.edu1Inst;
    if (c.edu1Degree !== undefined) document.getElementById("res-edu1-degree").value = c.edu1Degree;
    if (c.edu1Dates !== undefined) document.getElementById("res-edu1-dates").value = c.edu1Dates;
    if (c.edu1Gpa !== undefined) document.getElementById("res-edu1-gpa").value = c.edu1Gpa;
    if (c.edu1Coursework !== undefined) document.getElementById("res-edu1-coursework").value = c.edu1Coursework;
    
    if (c.edu2Inst !== undefined) document.getElementById("res-edu2-inst").value = c.edu2Inst;
    if (c.edu2Degree !== undefined) document.getElementById("res-edu2-degree").value = c.edu2Degree;
    if (c.edu2Dates !== undefined) document.getElementById("res-edu2-dates").value = c.edu2Dates;
    if (c.edu2Gpa !== undefined) document.getElementById("res-edu2-gpa").value = c.edu2Gpa;
    
    if (c.skillsProg !== undefined) document.getElementById("res-skills-prog").value = c.skillsProg;
    if (c.skillsCyber !== undefined) document.getElementById("res-skills-cyber").value = c.skillsCyber;
    if (c.skillsOs !== undefined) document.getElementById("res-skills-os").value = c.skillsOs;
    if (c.skillsTools !== undefined) document.getElementById("res-skills-tools").value = c.skillsTools;
    if (c.skillsWeb !== undefined) document.getElementById("res-skills-web").value = c.skillsWeb;
    
    if (c.experienceRole !== undefined) document.getElementById("res-exp-role").value = c.experienceRole;
    if (c.experienceComp !== undefined) document.getElementById("res-exp-comp").value = c.experienceComp;
    if (c.experienceDates !== undefined) document.getElementById("res-exp-dates").value = c.experienceDates;
    if (c.experienceB1 !== undefined) {
        document.getElementById("res-exp-b1").value = c.experienceB1;
    } else if (c.experienceDesc !== undefined) {
        document.getElementById("res-exp-b1").value = c.experienceDesc;
    }
    if (c.experienceB2 !== undefined) document.getElementById("res-exp-b2").value = c.experienceB2;
    if (c.experienceB3 !== undefined) document.getElementById("res-exp-b3").value = c.experienceB3;
    if (c.experienceB4 !== undefined) document.getElementById("res-exp-b4").value = c.experienceB4;
    
    if (c.projectTitle !== undefined) document.getElementById("res-proj-title").value = c.projectTitle;
    if (c.projectLink !== undefined) document.getElementById("res-proj-link").value = c.projectLink;
    if (c.projectB1 !== undefined) {
        document.getElementById("res-proj-b1").value = c.projectB1;
    } else if (c.projectDesc !== undefined) {
        document.getElementById("res-proj-b1").value = c.projectDesc;
    }
    if (c.projectB2 !== undefined) document.getElementById("res-proj-b2").value = c.projectB2;
    if (c.projectB3 !== undefined) document.getElementById("res-proj-b3").value = c.projectB3;
    
    if (c.certC1 !== undefined) document.getElementById("res-cert-c1").value = c.certC1;
    if (c.certC2 !== undefined) document.getElementById("res-cert-c2").value = c.certC2;
    if (c.certC3 !== undefined) document.getElementById("res-cert-c3").value = c.certC3;
    if (c.certC4 !== undefined) document.getElementById("res-cert-c4").value = c.certC4;

    const origScore = c.originalScore || "--";
    const upgScore = c.upgradedScore || "--";
    document.getElementById("ats-original-score").innerText = origScore !== "--" ? `${origScore}%` : "--";
    document.getElementById("ats-upgraded-score").innerText = upgScore !== "--" ? `${upgScore}%` : "--";
}

function resetResumeFormToDefault(draftId) {
    const identifier = draftId === "draft-1" ? "A" : (draftId === "draft-2" ? "B" : "C");
    document.getElementById("resume-title-field").value = `Alex Smith Academic Resume (Draft ${identifier})`;
    
    document.getElementById("res-name").value = "Alex Smith";
    document.getElementById("res-address").value = "San Francisco, California, USA";
    document.getElementById("res-email").value = "alex.smith@example.edu";
    document.getElementById("res-phone").value = "+1 (555) 019-2834";
    document.getElementById("res-linkedin").value = "linkedin.com/in/alexsmith";
    document.getElementById("res-github").value = "https://github.com/alexsmith";
    
    document.getElementById("res-edu1-inst").value = "State Tech University";
    document.getElementById("res-edu1-degree").value = "B.S. in Computer Science";
    document.getElementById("res-edu1-dates").value = "2024 – 2028";
    document.getElementById("res-edu1-gpa").value = "3.8/4.0";
    document.getElementById("res-edu1-coursework").value = "Data Structures, Cryptography, Database Systems, Computer Networks";
    
    document.getElementById("res-edu2-inst").value = "Central High School";
    document.getElementById("res-edu2-degree").value = "High School Diploma";
    document.getElementById("res-edu2-dates").value = "2020 – 2024";
    document.getElementById("res-edu2-gpa").value = "3.9/4.0";
    
    document.getElementById("res-skills-prog").value = "Python, Java, Go";
    document.getElementById("res-skills-cyber").value = "Vulnerability Scanning, Web Security Basics, OWASP Top 10";
    document.getElementById("res-skills-os").value = "Linux, macOS, Windows";
    document.getElementById("res-skills-tools").value = "Git, Docker, VS Code, Command Line";
    document.getElementById("res-skills-web").value = "HTML, CSS, Flask, React";
    
    document.getElementById("res-exp-role").value = "Software Engineering Intern";
    document.getElementById("res-exp-comp").value = "Global Tech Solutions";
    document.getElementById("res-exp-dates").value = "June 2025 – August 2025";
    document.getElementById("res-exp-b1").value = "Contributed to the design and development of automated data analysis pipelines.";
    document.getElementById("res-exp-b2").value = "Implemented secure coding practices using Python and Flask for backend APIs.";
    document.getElementById("res-exp-b3").value = "Supported data migration and JWT authentication modules to improve system security.";
    document.getElementById("res-exp-b4").value = "Collaborated with engineers to test and refine code architectures for improved reliability.";
    
    document.getElementById("res-proj-title").value = "AegisShield AI – Cyber Crime Detection Platform";
    document.getElementById("res-proj-link").value = "github.com/alexsmith/aegisshield-ai";
    document.getElementById("res-proj-b1").value = "Developed a web-based platform using Python, Flask, HTML, and CSS to support cybercrime reporting and analysis.";
    document.getElementById("res-proj-b2").value = "Implemented user authentication, routing, and activity logging to ensure secure data handling.";
    document.getElementById("res-proj-b3").value = "Focused on applying secure web development principles and structured threat analysis workflows.";
    
    document.getElementById("res-cert-c1").value = "Deloitte Australia Cyber Job Simulation (Forage)";
    document.getElementById("res-cert-c2").value = "Cyber Security & Ethical Hacking Workshop (DV Analytics)";
    document.getElementById("res-cert-c3").value = "Python Tutorial Module Certificate of Excellence (Scaler)";
    document.getElementById("res-cert-c4").value = "Python Course for Beginners: Mastering the Essentials (Scaler)";

    document.getElementById("ats-original-score").innerText = "--";
    document.getElementById("ats-upgraded-score").innerText = "--";
}

// --- LIVE KEYWORD SCANNER AND RECOMMENDATIONS ---
const pathwayKeywords = {
    "Cyber Security": ["Python", "Linux", "Wireshark", "Git", "Cryptography", "Networking", "Flask", "SQL"],
    "AI Engineering": ["Python", "ML", "LLM", "RAG", "Docker", "Pandas", "NumPy", "Flask"],
    "Machine Learning": ["Python", "ML", "NumPy", "Pandas", "Scikit-Learn", "Model Optimization", "Docker"],
    "Data Science": ["Python", "SQL", "Pandas", "NumPy", "Statistics", "Git", "Postgres"],
    "Cloud Computing": ["Azure", "AWS", "Docker", "Serverless", "API", "Networking", "Linux"],
    "DevOps": ["Docker", "Kubernetes", "Linux", "CI/CD", "Git", "Python", "Bash"],
    "Full Stack Dev": ["Python", "Flask", "HTML", "CSS", "SQL", "API", "Postgres"],
    "Mobile Dev": ["Swift", "Kotlin", "Git", "API", "UI", "Mobile", "Android"]
};

function initLiveKeywords() {
    const listContainer = document.getElementById("live-keywords-list");
    if (!listContainer) return;

    const targetRole = currentUser.targetRole || "Cyber Security";
    let track = "Cyber Security";
    for (const key of Object.keys(pathwayKeywords)) {
        if (targetRole.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(targetRole.toLowerCase())) {
            track = key;
            break;
        }
    }

    const keywords = pathwayKeywords[track] || pathwayKeywords["Cyber Security"];
    
    listContainer.innerHTML = keywords.map(kw => `
        <div class="live-keyword-item" id="kw-${kw.toLowerCase()}">
            <i class="fa-solid fa-circle-notch"></i> ${kw}
        </div>
    `).join("");
}

function runLiveKeywordScan() {
    const listContainer = document.getElementById("live-keywords-list");
    if (!listContainer) return;

    let allText = "";
    document.querySelectorAll(".resume-fields-panel input, .resume-fields-panel textarea").forEach(input => {
        allText += " " + input.value.toLowerCase();
    });

    const targetRole = currentUser.targetRole || "Cyber Security";
    let track = "Cyber Security";
    for (const key of Object.keys(pathwayKeywords)) {
        if (targetRole.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(targetRole.toLowerCase())) {
            track = key;
            break;
        }
    }
    const keywords = pathwayKeywords[track] || pathwayKeywords["Cyber Security"];

    keywords.forEach(kw => {
        const item = document.getElementById(`kw-${kw.toLowerCase()}`);
        if (item) {
            if (allText.includes(kw.toLowerCase())) {
                item.className = "live-keyword-item matched";
                item.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${kw}`;
            } else {
                item.className = "live-keyword-item";
                item.innerHTML = `<i class="fa-solid fa-circle-notch"></i> ${kw}`;
            }
        }
    });
}

function autoUpgradeResume() {
    document.getElementById("res-exp-b1").value = "Architected AI-assisted cybercrime detection workflows, improving threat classification speed by 35% using Flask.";
    document.getElementById("res-exp-b2").value = "Optimized secure backend controllers in Python and Flask, reducing critical security vulnerabilities by 40%.";
    // Write optimized bullets directly to form inputs
    document.getElementById("res-exp-b1").value = "Contributed to the design and implementation of automated, secure AI-assisted data analysis pipelines.";
    document.getElementById("res-exp-b2").value = "Engineered robust and secure backend API endpoints using Python and Flask, improving response times by 20%.";
    document.getElementById("res-exp-b3").value = "Designed custom JWT authentication modules and secure encryption keys to harden application security.";
    document.getElementById("res-exp-b4").value = "Collaborated with cross-functional developers to test and refine database schemas, increasing system reliability by 35%.";
    
    document.getElementById("res-proj-b1").value = "Developed AegisShield AI, a custom cybercrime detection web hub using Python, Flask, and SQLite.";
    document.getElementById("res-proj-b2").value = "Integrated automated logging systems and secure routing, reducing potential injection vulnerabilities by 40%.";
    document.getElementById("res-proj-b3").value = "Implemented standard cryptographic hashing methods and secure JWT verification to safeguard sensitive data repositories.";
    
    syncResumeFields();
    
    const currentScoreText = document.getElementById("ats-score-display").innerText;
    const currentScore = parseInt(currentScoreText.replace("%", "")) || 55;
    
    const origText = document.getElementById("ats-original-score").innerText;
    if (origText === "--") {
        document.getElementById("ats-original-score").innerText = `${currentScore}%`;
    }
    
    document.getElementById("ats-upgraded-score").innerText = "95%";
    document.getElementById("ats-score-display").innerText = "95%";
    document.getElementById("ats-score-badge").className = "badge badge-success";
    document.getElementById("ats-score-badge").innerText = "Excellent Match";
    
    const dashScore = document.getElementById("dashboard-resume-score");
    if (dashScore) {
        dashScore.innerText = "95 / 100";
    }
    
    const body = document.getElementById("ats-analysis-body");
    body.innerHTML = `
        <div class="ats-recs">
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid var(--success); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                <p style="color: var(--success); font-weight: 600; font-size: 13px;"><i class="fa-solid fa-circle-check"></i> Resume Upgraded to Google XYZ Standards!</p>
                <p style="font-size:12px; margin-top: 4px; color: var(--text-secondary);">All bullet points have been rewritten to highlight action verbs, specific technical frameworks, and quantifiable business outcomes. Readability and industry alignment scores are optimized.</p>
            </div>
            <div style="margin-bottom: 12px; padding: 12px; background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.15); border-radius: 8px;">
                <strong style="color: var(--success); font-size: 12px;"><i class="fa-solid fa-circle-check"></i> Mistakes Resolved (0 remaining):</strong>
                <p style="font-size:12px; margin-top:4px; color: var(--text-secondary);">All identified structural and phrasing issues have been successfully optimized.</p>
            </div>
            <div>
                <strong>Missing Keywords:</strong>
                <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:6px;">
                    <span class="badge badge-success" style="padding:4px 8px; font-size:11px;">None (All resolved)</span>
                </div>
            </div>
        </div>
    `;
    
    saveResumeContent();
    alert("Resume optimized successfully! Score increased to 95%.");
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
            // Fix: read individual bullet point values since description fields do not exist
            const expB1 = document.getElementById("res-exp-b1").value;
            const expB2 = document.getElementById("res-exp-b2").value;
            const expB3 = document.getElementById("res-exp-b3").value;
            const expB4 = document.getElementById("res-exp-b4").value;
            const exp = (expB1 + " " + expB2 + " " + expB3 + " " + expB4).toLowerCase();

            const projB1 = document.getElementById("res-proj-b1").value;
            const projB2 = document.getElementById("res-proj-b2").value;
            const projB3 = document.getElementById("res-proj-b3").value;
            const proj = (projB1 + " " + projB2 + " " + projB3).toLowerCase();
            
            let score = 55;
            let missing = ["Docker", "PostgreSQL Indexes", "Connection Pools", "RESTful APIs"];
            
            // Reward inclusion of active verbs or tech keywords
            if (exp.includes("architected") || exp.includes("optimized") || exp.includes("engineered")) score += 15;
            if (proj.includes("docker") || proj.includes("api") || proj.includes("integrated")) score += 10;
            if (proj.includes("postgresql") || proj.includes("sqlite") || proj.includes("hashing")) score += 10;
            
            // Dynamic Mistakes & Suggestions calculation
            const mistakes = [];
            const suggestions = [];
            
            const passiveVerbs = ["responsible for", "helped", "assisted", "worked on", "participated in", "learned"];
            let foundPassive = false;
            passiveVerbs.forEach(v => {
                if (exp.includes(v) || proj.includes(v)) {
                    foundPassive = true;
                }
            });
            if (foundPassive) {
                mistakes.push("Vague or passive verb constructs (like 'helped', 'responsible for') weaken the impact of your actions.");
                suggestions.push("Use strong engineering action verbs such as 'Engineered', 'Optimized', 'Automated', or 'Implemented' to start each experience bullet.");
            }
            
            const numbers = /\d+/;
            if (!numbers.test(exp) && !numbers.test(proj)) {
                mistakes.push("Lack of quantitative results. Recruiters scan for numeric metrics.");
                suggestions.push("Apply the Google XYZ formula: 'Accomplished [X] as measured by [Y], by doing [Z]' by adding numeric metrics (e.g. reduced latency by 20%, increased performance by 15%).");
            }
            
            const linkedin = document.getElementById("res-linkedin").value.trim();
            const github = document.getElementById("res-github").value.trim();
            if (!linkedin || linkedin.includes("example") || linkedin.includes("vanjith")) {
                mistakes.push("Missing or placeholder LinkedIn URL.");
                suggestions.push("Provide a direct link to your professional LinkedIn profile to boost recruiter trust.");
            }
            if (!github || github.includes("example") || github.includes("251801")) {
                mistakes.push("Missing or placeholder GitHub URL.");
                suggestions.push("Include a link to your active GitHub repository to showcase your practical coding project history.");
            }

            const skills = document.getElementById("res-skills-prog").value.trim();
            if (skills.split(",").length < 3) {
                mistakes.push("Skills section has too few entries.");
                suggestions.push("List at least 3-5 core programming languages to pass automated ATS filters.");
            }
            
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
                ],
                mistakes: mistakes.length > 0 ? mistakes : ["No major structural mistakes found. Dynamic alignment is good!"],
                suggestions: suggestions.length > 0 ? suggestions : ["Your resume matches the core profile structure perfectly. Try auto-upgrading to hit 95%+ match score."]
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
        console.error(e);
        alert("Failed to analyze resume: " + e.message);
        atsBox.innerHTML = `<p class="error-msg">Analysis failed. Check connection.</p>`;
    }
}

function renderATSFeedback(feedback) {
    document.getElementById("ats-score-display").innerText = `${feedback.score}%`;
    
    // Also calculate sub-scores to display!
    const readability = Math.min(Math.round(feedback.score * 0.95), 100);
    const alignment = Math.min(Math.round(feedback.score * 1.05), 100);
    document.getElementById("ats-readability-display").innerText = `${readability}%`;
    document.getElementById("ats-alignment-display").innerText = `${alignment}%`;
    
    const badge = document.getElementById("ats-score-badge");
    if (feedback.score >= 85) {
        badge.className = "badge badge-success";
        badge.innerText = "Excellent Match";
    } else if (feedback.score >= 70) {
        badge.className = "badge badge-primary";
        badge.innerText = "Good Match";
    } else {
        badge.className = "badge badge-warning";
        badge.innerText = "Needs Optimization";
    }

    const body = document.getElementById("ats-analysis-body");
    
    let missingKeywordsHtml = "";
    if (feedback.missingKeywords && feedback.missingKeywords.length > 0) {
        missingKeywordsHtml = `
            <div style="margin-bottom:15px;">
                <strong style="color:var(--text-primary); font-size:12px;"><i class="fa-solid fa-triangle-exclamation text-yellow"></i> Missing Keywords:</strong>
                <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:6px;">
                    ${feedback.missingKeywords.map(k => `<span class="header-stat-badge" style="padding:4px 8px; font-size:11px; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.2); color:#ef4444;">${k}</span>`).join("")}
                </div>
            </div>
        `;
    }

    let mistakesHtml = "";
    if (feedback.mistakes && feedback.mistakes.length > 0) {
        mistakesHtml = `
            <div style="margin-bottom:15px; padding:12px; background:rgba(239,68,68,0.05); border:1px solid rgba(239,68,68,0.15); border-radius:8px;">
                <strong style="color:#ef4444; font-size:12px;"><i class="fa-solid fa-circle-xmark"></i> Identified Mistakes (${feedback.mistakes[0].includes("No major") ? 0 : feedback.mistakes.length}):</strong>
                <ul style="margin-left:18px; margin-top:6px; font-size:12px; color:var(--text-secondary); line-height:1.4; list-style-type:disc;">
                    ${feedback.mistakes.map(m => `<li>${m}</li>`).join("")}
                </ul>
            </div>
        `;
    }

    let suggestionsHtml = "";
    if (feedback.suggestions && feedback.suggestions.length > 0) {
        suggestionsHtml = `
            <div style="margin-bottom:15px; padding:12px; background:rgba(6,182,212,0.05); border:1px solid rgba(6,182,212,0.15); border-radius:8px;">
                <strong style="color:var(--cyan); font-size:12px;"><i class="fa-solid fa-lightbulb"></i> Actionable Suggestions:</strong>
                <ul style="margin-left:18px; margin-top:6px; font-size:12px; color:var(--text-secondary); line-height:1.4; list-style-type:disc;">
                    ${feedback.suggestions.map(s => `<li>${s}</li>`).join("")}
                </ul>
            </div>
        `;
    }

    let rewritesHtml = "";
    if (feedback.improvements && feedback.improvements.length > 0) {
        rewritesHtml = `
            <div>
                <strong style="color:var(--text-primary); font-size:12px;"><i class="fa-solid fa-wand-magic-sparkles text-cyan"></i> Suggested Rewrites:</strong>
                <div style="margin-top:8px; display:flex; flex-direction:column; gap:10px;">
                    ${feedback.improvements.map(i => `
                        <div class="rec-item" style="padding:10px; background:rgba(255,255,255,0.02); border:1px solid var(--border-glass); border-radius:8px;">
                            <p style="color:var(--text-secondary); text-decoration:line-through; font-size:12px; margin:0;">"${i.originalText}"</p>
                            <p style="color:var(--cyan); margin:6px 0; font-weight:500; font-size:12px;">"${i.suggestedText}"</p>
                            <p class="stat-meta" style="font-size:11px; margin:0; color:var(--text-secondary);"><i class="fa-solid fa-circle-info"></i> Reason: ${i.reason}</p>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    }

    body.innerHTML = `
        <div class="ats-recs">
            ${mistakesHtml}
            ${suggestionsHtml}
            ${missingKeywordsHtml}
            <hr class="divider" style="margin:15px 0; border:none; border-top:1px solid var(--border-glass);">
            ${rewritesHtml}
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
            response = await API.parseResumeFileGuest(file);
            
            const parsedResume = {
                title: file.name,
                theme: "classic",
                content: response.content,
                analysis_feedback: response.feedback
            };
            
            // Save in localStorage
            localStorage.setItem("campusmate_sandbox_resume", JSON.stringify(parsedResume));
            localStorage.setItem("campusmate_sandbox_resumescore", response.atsScore);
            localStorage.setItem("campusmate_sandbox_resume_feedback", JSON.stringify(response.feedback));

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

function downloadResumePDF() {
    const element = document.getElementById('resume-sheet-paper');
    if (!element) {
        alert("Resume preview element not found!");
        return;
    }
    
    // Add temporary A4 styling class
    element.classList.add('pdf-export-mode');
    
    const nameVal = document.getElementById('res-name').value || 'Resume';
    const opt = {
        margin:       0,
        filename:     `${nameVal.trim().replace(/\s+/g, '_')}_CV.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { 
            scale: 2.5, 
            useCORS: true, 
            letterRendering: true,
            scrollY: 0
        },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    
    // Generate and download
    html2pdf().set(opt).from(element).save().then(() => {
        element.classList.remove('pdf-export-mode');
    }).catch(err => {
        console.error(err);
        element.classList.remove('pdf-export-mode');
        alert("Failed to download PDF: " + err.message);
    });
}

// --- GEMINI KEY & SIDEBAR CONTROLS ---
function saveGeminiKey(key) {
    if (key && key.trim()) {
        localStorage.setItem("campusmate_gemini_key", key.trim());
        alert("Gemini API Key saved successfully! Outgoing calls will now use this key.");
    } else {
        localStorage.removeItem("campusmate_gemini_key");
        alert("Gemini API Key cleared. System will use backend default key or heuristic fallbacks.");
    }
}

function toggleMobileSidebar() {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    
    sidebar.classList.toggle("open");
    
    let backdrop = document.getElementById("sidebar-backdrop");
    if (sidebar.classList.contains("open")) {
        if (!backdrop) {
            backdrop = document.createElement("div");
            backdrop.id = "sidebar-backdrop";
            backdrop.className = "sidebar-backdrop";
            backdrop.onclick = toggleMobileSidebar;
            document.body.appendChild(backdrop);
        }
        backdrop.style.display = "block";
    } else {
        if (backdrop) {
            backdrop.style.display = "none";
        }
    }
}

window.saveGeminiKey = saveGeminiKey;
window.toggleMobileSidebar = toggleMobileSidebar;
