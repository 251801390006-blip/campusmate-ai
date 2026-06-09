// CampusMate AI — Floating AI Mentor Drawer Controller v2.0

// ── Drawer open/close ─────────────────────────────────────────────────────
function toggleMentorDrawer() {
    const drawer = document.getElementById("mentor-drawer");
    const arrow  = document.getElementById("mentor-arrow-icon");
    if (!drawer) return;
    drawer.classList.toggle("active");
    if (drawer.classList.contains("active")) {
        if (arrow) arrow.className = "fa-solid fa-chevron-down";
        loadMentorChatHistory();
    } else {
        if (arrow) arrow.className = "fa-solid fa-chevron-up";
    }
}

// ── HTML escape ───────────────────────────────────────────────────────────
function escapeHtml(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ── Markdown renderer ─────────────────────────────────────────────────────
function parseMarkdown(text) {
    let html = escapeHtml(text);

    // Headers
    html = html.replace(/###\s*(.*?)(?:<br>|$)/g, '<h5 class="fw-bold mt-2 mb-1" style="font-size:0.85rem;color:var(--text-primary);">$1</h5>');
    html = html.replace(/##\s*(.*?)(?:<br>|$)/g,  '<h4 class="fw-bold mt-2 mb-1" style="font-size:0.9rem;color:var(--text-primary);">$1</h4>');

    // Code inline
    html = html.replace(/`([^`]+)`/g, '<code style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;font-size:0.8em;font-family:monospace;">$1</code>');

    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong style="color:var(--text-primary);">$1</strong>');
    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');

    // Numbered list
    html = html.replace(/(?:^|<br>)\s*(\d+)\.\s+(.*?)(?=<br>|$)/g,
        '<div class="d-flex align-items-start gap-2 ms-1 my-1"><span class="fw-bold text-primary" style="min-width:16px;font-size:0.8rem;">$1.</span><div>$2</div></div>');

    // Bullet list
    html = html.replace(/(?:^|<br>)\s*[-*]\s+(.*?)(?=<br>|$)/g,
        '<div class="d-flex align-items-start gap-2 ms-2 my-1"><i class="fa-solid fa-circle text-primary mt-1" style="font-size:0.35rem;flex-shrink:0;margin-top:6px;"></i><div>$1</div></div>');

    // Markdown links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g,
        '<a href="$2" target="_blank" class="fw-semibold text-primary" style="text-decoration:underline;">$1</a>');

    // Newlines
    html = html.replace(/\n/g, '<br>');

    return html;
}

// ── Rich nav-card renderer ────────────────────────────────────────────────
function renderRichComponentCards(containerEl, markdownText) {
    const cardData = [
        { url: "/roadmaps",           icon: "fa-circle-nodes", title: "Roadmap Engine",         desc: "Access your 200-node visual career tree." },
        { url: "/resume-analyzer",    icon: "fa-id-card",      title: "Resume Builder",          desc: "Upload and analyse ATS keywords." },
        { url: "/interview-simulator",icon: "fa-microphone",   title: "Interview Simulator",     desc: "Practice technical questions with AI feedback." },
        { url: "/project-architect",  icon: "fa-sitemap",      title: "Project Architect",       desc: "Design DB schemas and file trees instantly." },
        { url: "/internship-center",  icon: "fa-briefcase",    title: "Internship Center",       desc: "Browse matched openings and eligibility." }
    ];
    cardData.forEach(item => {
        if (markdownText.includes(item.url)) {
            const card = document.createElement("div");
            card.className = "animate-fade-in border rounded p-3 mt-2 d-flex justify-content-between align-items-center";
            card.style.cssText = "border-left:3px solid #0078d4 !important; background:var(--bg-primary);";
            card.innerHTML = `
                <div class="d-flex align-items-center gap-3">
                    <div style="background:rgba(0,120,212,.1);color:#0078d4;width:38px;height:38px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;">
                        <i class="fa-solid ${item.icon}"></i>
                    </div>
                    <div>
                        <strong style="font-size:0.8rem;display:block;">${item.title}</strong>
                        <span class="text-secondary" style="font-size:0.7rem;">${item.desc}</span>
                    </div>
                </div>
                <a href="${item.url}" style="background:#0078d4;color:white;border:none;padding:4px 12px;border-radius:4px;font-size:0.72rem;font-weight:600;text-decoration:none;">Open</a>`;
            containerEl.appendChild(card);
        }
    });
}

// ── Streaming word-by-word effect ─────────────────────────────────────────
function streamReplyEffect(element, fullText, callback) {
    const htmlFormatted = parseMarkdown(fullText);
    const words = htmlFormatted.split(" ");
    let i = 0;
    element.innerHTML = '<span class="streaming-cursor" style="opacity:0.7;animation:blink 1s step-end infinite;">▋</span>';

    const timer = setInterval(() => {
        if (i < words.length) {
            element.innerHTML = words.slice(0, i + 1).join(" ") +
                ' <span class="streaming-cursor" style="opacity:0.7;">▋</span>';
            i++;
            const box = document.getElementById("mentor-chat-messages");
            if (box) box.scrollTop = box.scrollHeight;
        } else {
            clearInterval(timer);
            element.innerHTML = htmlFormatted;
            if (callback) callback();
        }
    }, 16);
}

// ── Suggestion chips ──────────────────────────────────────────────────────
async function handleChipClick(text) {
    const drawer = document.getElementById("mentor-drawer");
    if (drawer && !drawer.classList.contains("active")) toggleMentorDrawer();
    await executeMentorQuery(text);
}

function updateSuggestionChips(lastQuery) {
    const container = document.getElementById("mentor-chat-chips");
    if (!container) return;
    const q = lastQuery.toLowerCase();
    let chips = [];
    if (q.includes("cert") || q.includes("credential"))
        chips = ["How to study for AZ-900?", "AWS practice projects", "Cert bullet points for resume"];
    else if (q.includes("project") || q.includes("recommend"))
        chips = ["Backend Express file structure", "What database should I use?", "DevOps CI/CD workflow"];
    else if (q.includes("resume") || q.includes("cv"))
        chips = ["Explain Google XYZ formula", "Suggest rewrites for intern role", "How to add missing keywords"];
    else if (q.includes("docker") || q.includes("container"))
        chips = ["Explain Docker multi-stage builds", "Map host directory volumes", "Draft docker-compose files"];
    else if (q.includes("interview") || q.includes("question"))
        chips = ["Give me a system design question", "What are behavioral STAR answers?", "Common Python interview Qs"];
    else
        chips = ["Recommend a project for my track", "What certifications should I get?", "Review my experience bullets"];

    container.innerHTML = chips.map(c =>
        `<button class="chip" onclick="handleChipClick('${c.replace(/'/g, "\\'")}')">${c}</button>`
    ).join("");
}

// ── Load chat history ─────────────────────────────────────────────────────
async function loadMentorChatHistory() {
    const messagesBox = document.getElementById("mentor-chat-messages");
    if (!messagesBox) return;
    try {
        const resp = await fetch("/ai-mentor/history");
        const data = await resp.json();
        if (resp.ok) {
            const memText = document.getElementById("mentor-memory-text");
            if (memText)
                memText.innerHTML = `Track: <strong>${data.track || "—"}</strong> | XP: <strong>${data.xp || 0}</strong> | Resume: <strong>${data.resume_score || 0}%</strong>`;
            if (data.history && data.history.length > 0) {
                messagesBox.innerHTML = "";
                data.history.forEach(h => {
                    const cls = h.sender === "user" ? "user" : "mentor";
                    const div = document.createElement("div");
                    div.className = `message ${cls} animate-fade-in`;
                    const p = document.createElement("p");
                    p.style.margin = "0";
                    p.innerHTML = parseMarkdown(h.content);
                    div.appendChild(p);
                    if (h.sender === "ai") renderRichComponentCards(div, h.content);
                    messagesBox.appendChild(div);
                });
                messagesBox.scrollTop = messagesBox.scrollHeight;
            }
        }
    } catch (e) { console.error("History load error:", e); }
}

// ── Send message ──────────────────────────────────────────────────────────
let _lastMsgTime = 0;

async function executeMentorQuery(msg) {
    if (!msg || !msg.trim()) return;
    const now = Date.now();
    if (now - _lastMsgTime < 2500) {
        showToast("Please wait a moment before sending another message.", "warning");
        return;
    }
    _lastMsgTime = now;

    const messagesBox = document.getElementById("mentor-chat-messages");
    if (!messagesBox) return;

    // Add user bubble
    const userDiv = document.createElement("div");
    userDiv.className = "message user animate-fade-in";
    userDiv.innerHTML = `<p style="margin:0;">${escapeHtml(msg)}</p>`;
    messagesBox.appendChild(userDiv);
    messagesBox.scrollTop = messagesBox.scrollHeight;

    // Add thinking spinner
    const thinkId = "thinking-" + Date.now();
    const thinkDiv = document.createElement("div");
    thinkDiv.className = "message mentor animate-fade-in";
    thinkDiv.id = thinkId;
    thinkDiv.innerHTML = `<p style="margin:0;"><i class="fa-solid fa-spinner fa-spin me-1 text-primary"></i> Thinking...</p>`;
    messagesBox.appendChild(thinkDiv);
    messagesBox.scrollTop = messagesBox.scrollHeight;

    // Get CSRF token — try meta tag first, then hidden input
    const csrfMeta  = document.querySelector('meta[name="csrf-token"]');
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    const csrf = (csrfMeta ? csrfMeta.content : null) || (csrfInput ? csrfInput.value : "") || "";

    // Get API key: global admin key takes priority, then personal user key
    const apiKey = localStorage.getItem("campusmate_global_ai_key") 
                || localStorage.getItem("campusmate_gemini_key") 
                || "";


    try {
        const resp = await fetch("/ai-mentor/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
            body: JSON.stringify({ message: msg, custom_key: apiKey })
        });
        const data = await resp.json();

        const thinking = document.getElementById(thinkId);
        if (thinking) thinking.remove();

        if (resp.ok && data.success) {
            const aiDiv = document.createElement("div");
            aiDiv.className = "message mentor animate-fade-in";
            const p = document.createElement("p");
            p.style.margin = "0";
            aiDiv.appendChild(p);
            messagesBox.appendChild(aiDiv);
            messagesBox.scrollTop = messagesBox.scrollHeight;

            streamReplyEffect(p, data.response, () => {
                renderRichComponentCards(aiDiv, data.response);
                messagesBox.scrollTop = messagesBox.scrollHeight;
                updateSuggestionChips(msg);
            });
        } else {
            const errDiv = document.createElement("div");
            errDiv.className = "message mentor animate-fade-in";
            errDiv.innerHTML = `<p style="margin:0;color:var(--danger);"><i class="fa-solid fa-triangle-exclamation me-1"></i>${escapeHtml(data.error || "Server error. Try again.")}</p>`;
            messagesBox.appendChild(errDiv);
            messagesBox.scrollTop = messagesBox.scrollHeight;
        }
    } catch (e) {
        console.error("Mentor fetch error:", e);
        const thinking = document.getElementById(thinkId);
        if (thinking) thinking.remove();
        const errDiv = document.createElement("div");
        errDiv.className = "message mentor animate-fade-in";
        errDiv.innerHTML = `<p style="margin:0;color:var(--danger);"><i class="fa-solid fa-wifi me-1"></i>Network error. Check your connection.</p>`;
        messagesBox.appendChild(errDiv);
        messagesBox.scrollTop = messagesBox.scrollHeight;
    }
}

async function sendMentorMessage(e) {
    if (e) e.preventDefault();
    const input = document.getElementById("mentor-user-input");
    if (!input) return;
    const msg = input.value.trim();
    if (!msg) return;
    input.value = "";
    await executeMentorQuery(msg);
}

// ── Toast helper ──────────────────────────────────────────────────────────
function showToast(message, type = "info") {
    let container = document.getElementById("toast-container-main");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container-main";
        container.className = "toast-container-custom";
        document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `toast-custom ${type}`;
    const icons = { success: "fa-circle-check", danger: "fa-triangle-exclamation", warning: "fa-exclamation-circle", info: "fa-circle-info" };
    toast.innerHTML = `<i class="fa-solid ${icons[type] || icons.info} me-1"></i>${escapeHtml(message)}`;
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = "0"; toast.style.transition = "opacity 0.4s"; setTimeout(() => toast.remove(), 400); }, 3500);
}

// ── API Key Management ────────────────────────────────────────────────────
function updateApiKeyStatus() {
    const globalKey = localStorage.getItem("campusmate_global_ai_key") || "";
    const userKey   = localStorage.getItem("campusmate_gemini_key") || "";
    const key = globalKey || userKey;
    const statusEl = document.getElementById("mentor-api-status");
    if (!statusEl) return;
    if (key) {
        const provider = key.startsWith("gsk_") ? "Groq" : "Gemini";
        const source   = globalKey ? "Admin" : "Personal";
        const masked   = key.substring(0, 8) + "..." + key.slice(-4);
        statusEl.innerHTML = `<i class="fa-solid fa-circle" style="font-size:0.4rem;color:#22c55e;margin-right:4px;"></i>🟢 ${provider} AI Online (${source} Key)`;
    } else {
        statusEl.innerHTML = `<i class="fa-solid fa-circle" style="font-size:0.4rem;color:#ef4444;margin-right:4px;"></i>No API Key — Add key in Settings to activate AI`;
    }
}


function toggleMentorApiKey() {
    const form = document.getElementById("mentor-api-key-form");
    if (!form) return;
    const isHidden = form.style.display === "none" || form.style.display === "";
    form.style.display = isHidden ? "block" : "none";
    if (isHidden) {
        const existing = localStorage.getItem("campusmate_gemini_key") || "";
        const input = document.getElementById("mentor-api-key-input");
        if (input && existing) input.value = existing;
    }
}

async function saveMentorApiKey() {
    const input = document.getElementById("mentor-api-key-input");
    if (!input) return;
    const key = input.value.trim();
    if (!key || key.length < 10) {
        showToast("Please enter a valid API key (Groq: gsk_... or Gemini: AIza...)", "warning");
        return;
    }

    // Always save locally so this browser session works immediately
    localStorage.setItem("campusmate_gemini_key", key);
    updateApiKeyStatus();

    const form = document.getElementById("mentor-api-key-form");
    if (form) form.style.display = "none";

    const provider = key.startsWith("gsk_") ? "Groq LLaMA 3.3-70B" : "Gemini 2.5 Flash";

    // Also save to the SERVER DATABASE so ALL users / all devices benefit permanently
    try {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrf = csrfMeta ? csrfMeta.content : "";
        const resp = await fetch("/admin/global-ai-key", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
            body: JSON.stringify({ api_key: key })
        });
        const data = await resp.json();
        if (data.success) {
            const messagesBox = document.getElementById("mentor-chat-messages");
            if (messagesBox) {
                const sysDiv = document.createElement("div");
                sysDiv.className = "message mentor animate-fade-in";
                sysDiv.innerHTML = `<p style="margin:0;"><i class="fa-solid fa-circle-check text-success me-1"></i><strong>API key saved to server!</strong> Now using <strong>${provider}</strong>. All students can now chat with AI. Ask me anything!</p>`;
                messagesBox.appendChild(sysDiv);
                messagesBox.scrollTop = messagesBox.scrollHeight;
            }
            showToast(`✅ ${provider} connected for ALL users!`, "success");
        } else {
            // Non-admin user: key saved locally only (works for them personally)
            const messagesBox = document.getElementById("mentor-chat-messages");
            if (messagesBox) {
                const sysDiv = document.createElement("div");
                sysDiv.className = "message mentor animate-fade-in";
                sysDiv.innerHTML = `<p style="margin:0;"><i class="fa-solid fa-circle-check text-success me-1"></i><strong>API key saved!</strong> Now using <strong>${provider}</strong>. Ask me anything!</p>`;
                messagesBox.appendChild(sysDiv);
                messagesBox.scrollTop = messagesBox.scrollHeight;
            }
            showToast(`✅ ${provider} connected!`, "success");
        }
    } catch (e) {
        // Network error saving to server — still works locally
        const messagesBox = document.getElementById("mentor-chat-messages");
        if (messagesBox) {
            const sysDiv = document.createElement("div");
            sysDiv.className = "message mentor animate-fade-in";
            sysDiv.innerHTML = `<p style="margin:0;"><i class="fa-solid fa-circle-check text-success me-1"></i><strong>API key saved!</strong> Now using <strong>${provider}</strong>. Ask me anything!</p>`;
            messagesBox.appendChild(sysDiv);
            messagesBox.scrollTop = messagesBox.scrollHeight;
        }
        showToast(`✅ ${provider} connected!`, "success");
    }
}


function clearMentorApiKey() {
    localStorage.removeItem("campusmate_gemini_key");
    const input = document.getElementById("mentor-api-key-input");
    if (input) input.value = "";
    updateApiKeyStatus();
    const form = document.getElementById("mentor-api-key-form");
    if (form) form.style.display = "none";
    showToast("API key removed. AI is now offline.", "warning");
}

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    updateApiKeyStatus();
    loadMentorChatHistory();

    // Enter key sends message
    const input = document.getElementById("mentor-user-input");
    if (input) {
        input.addEventListener("keydown", e => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMentorMessage(null);
            }
        });
    }
});
