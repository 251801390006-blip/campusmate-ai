// CampusMate AI Client API Service Library
const API = {
    baseUrl: "", // relative URL

    getToken() {
        return localStorage.getItem("campusmate_token");
    },

    setToken(token) {
        localStorage.setItem("campusmate_token", token);
    },

    clearToken() {
        localStorage.removeItem("campusmate_token");
    },

    isLoggedIn() {
        return !!this.getToken();
    },

    async request(endpoint, options = {}) {
        const token = this.getToken();
        
        // Setup headers
        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {})
        };
        
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }

        const geminiKey = localStorage.getItem("campusmate_gemini_key");
        if (geminiKey) {
            headers["X-Gemini-API-Key"] = geminiKey;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || "Something went wrong.");
            }
            return data;
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            throw error;
        }
    },

    // --- AUTHENTICATION ---
    async register(email, password, fullName, academicLevel) {
        const res = await this.request("/api/auth/register", {
            method: "POST",
            body: JSON.stringify({ email, password, fullName, academicLevel })
        });
        if (res.token) this.setToken(res.token);
        return res;
    },

    async login(email, password) {
        const res = await this.request("/api/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password })
        });
        if (res.token) this.setToken(res.token);
        return res;
    },

    async getMe() {
        return this.request("/api/auth/me");
    },

    async updateProfile(fullName, academicLevel, institution, targetRole) {
        return this.request("/api/auth/profile", {
            method: "PUT",
            body: JSON.stringify({ fullName, academicLevel, institution, targetRole })
        });
    },

    // --- ROADMAPS ---
    async generateRoadmap(targetRole, skills = []) {
        return this.request("/api/roadmaps/generate", {
            method: "POST",
            body: JSON.stringify({ targetRole, skills })
        });
    },

    async getActiveRoadmap() {
        return this.request("/api/roadmaps/active");
    },

    async updateNodeStatus(nodeId, status) {
        return this.request(`/api/roadmaps/nodes/${nodeId}/status`, {
            method: "PATCH",
            body: JSON.stringify({ status })
        });
    },

    // --- RESUMES ---
    async getResumes() {
        return this.request("/api/resumes");
    },

    async saveResume(title, theme, content) {
        return this.request("/api/resumes", {
            method: "POST",
            body: JSON.stringify({ title, theme, content })
        });
    },

    async analyzeResume(targetJobDescription) {
        return this.request("/api/resumes/analyze", {
            method: "POST",
            body: JSON.stringify({ targetJobDescription })
        });
    },

    async uploadResumeFile(file) {
        const token = this.getToken();
        const formData = new FormData();
        formData.append("file", file);
        
        const headers = {};
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
        const geminiKey = localStorage.getItem("campusmate_gemini_key");
        if (geminiKey) {
            headers["X-Gemini-API-Key"] = geminiKey;
        }

        const response = await fetch(`${this.baseUrl}/api/resumes/upload`, {
            method: "POST",
            headers,
            body: formData
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Upload failed.");
        }
        return data;
    },

    async parseResumeFileGuest(file) {
        const formData = new FormData();
        formData.append("file", file);
        
        const headers = {};
        const geminiKey = localStorage.getItem("campusmate_gemini_key");
        if (geminiKey) {
            headers["X-Gemini-API-Key"] = geminiKey;
        }

        const response = await fetch(`${this.baseUrl}/api/resumes/parse-guest`, {
            method: "POST",
            headers,
            body: formData
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Guest parsing failed.");
        }
        return data;
    },

    // --- AI MENTOR ---
    async sendMentorMessage(message) {
        return this.request("/api/mentor/chat", {
            method: "POST",
            body: JSON.stringify({ message })
        });
    },

    // --- DASHBOARD & STATS ---
    async getDashboardStats() {
        return this.request("/api/dashboard/stats");
    }
};
window.API = API;
