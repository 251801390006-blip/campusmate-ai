// CampusMate AI Floating AI Mentor Drawer Controller

function toggleMentorDrawer() {
    const drawer = document.getElementById("mentor-drawer");
    const arrow = document.getElementById("mentor-arrow-icon");
    if (!drawer) return;
    drawer.classList.toggle("active");
    
    if (drawer.classList.contains("active")) {
        if (arrow) arrow.className = "fa-solid fa-chevron-down";
        loadMentorChatHistory();
    } else {
        if (arrow) arrow.className = "fa-solid fa-chevron-up";
    }
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Simple markdown parser to render headings, bold text, links and list items as styled HTML
function parseMarkdown(text) {
    let html = escapeHtml(text);
    
    // Convert headers (e.g. ### Header or **Header**)
    html = html.replace(/###\s*(.*?)(?:<br>|$)/g, '<h5 class="fw-bold text-dark mt-2 mb-1">$1</h5>');
    
    // Bold tags
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong class="text-dark fw-bold">$1</strong>');
    
    // Bullet list items
    html = html.replace(/(?:^|<br>)\s*-\s+(.*?)(?=<br>|$)/g, '<div class="d-flex align-items-start gap-2 ms-2 my-1"><i class="fa-solid fa-circle text-primary mt-1.5" style="font-size:0.4rem;"></i><div>$1</div></div>');
    
    // Emoji conversions or custom triggers
    html = html.replace(/👉/g, '<span class="text-primary fw-bold">👉</span>');
    html = html.replace(/🎯/g, '🎯');
    html = html.replace(/📝/g, '📝');
    html = html.replace(/🎙️/g, '🎙️');
    html = html.replace(/🌐/g, '🌐');
    html = html.replace(/🏗️/g, '🏗️');
    html = html.replace(/💼/g, '💼');
    
    // Standard markdown links [text](url) -> standard anchors
    // Note: escapeHtml makes links contain &quot; or similar if quotes are inside url. Let's make it robust:
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="fw-bold text-primary border-bottom border-primary pb-0.5">$1</a>');
    
    // Replace newlines with <br>
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

// Extract any system navigation URLs from the response to append rich component cards
function renderRichComponentCards(containerEl, markdownText) {
    const cardData = [
        { url: "/roadmaps", icon: "fa-circle-nodes", title: "Roadmap Engine", desc: "Access your 200-node visual career tree." },
        { url: "/resume-analyzer", icon: "fa-id-card", title: "Resume Builder", desc: "Upload and analyze ATS keywords checklist." },
        { url: "/interview-simulator", icon: "fa-microphone", title: "AI Interview Simulator", desc: "Practice technical cards with local text-to-speech." },
        { url: "/project-architect", icon: "fa-sitemap", title: "AI Project Architect", desc: "Design database schemas and file trees." },
        { url: "/internship-center", icon: "fa-briefcase", title: "Internship Command Center", desc: "Check matched openings and eligibility ratings." }
    ];
    
    // Find all urls mentioned in the markdown
    cardData.forEach(item => {
        if (markdownText.includes(item.url)) {
            const card = document.createElement("div");
            card.className = "rich-nav-card shadow-sm border rounded p-3 mt-3 d-flex justify-content-between align-items-center bg-white animate-pop";
            card.style.borderLeft = "4px solid #0078d4 !important";
            card.style.background = "#fafbfc";
            
            card.innerHTML = `
                <div class="d-flex align-items-center gap-3">
                    <div style="background: rgba(0, 120, 212, 0.08); color: #0078d4; width: 42px; height: 42px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.25rem;">
                        <i class="fa-solid ${item.icon}"></i>
                    </div>
                    <div>
                        <strong class="d-block text-dark" style="font-size: 0.8rem; font-weight: 700;">${item.title}</strong>
                        <span class="text-secondary" style="font-size: 0.72rem;">${item.desc}</span>
                    </div>
                </div>
                <a href="${item.url}" class="btn btn-sm btn-outline-primary" style="font-size: 0.75rem; font-weight: 600; padding: 4px 12px; border-radius: 4px;">Launch <i class="fa-solid fa-arrow-right ms-1"></i></a>
            `;
            containerEl.appendChild(card);
        }
    });
}

// Simulate word-by-word streaming effect
function streamReplyEffect(element, fullText, callback) {
    const htmlFormatted = parseMarkdown(fullText);
    const words = htmlFormatted.split(" ");
    let i = 0;
    
    // Set up cursor
    element.innerHTML = '<span class="streaming-cursor">▋</span>';
    
    const speed = 18; // milliseconds per word
    const timer = setInterval(() => {
        if (i < words.length) {
            const currentSubtext = words.slice(0, i + 1).join(" ");
            element.innerHTML = currentSubtext + ' <span class="streaming-cursor">▋</span>';
            i++;
            
            // Auto-scroll
            const messagesBox = document.getElementById("mentor-chat-messages");
            if (messagesBox) messagesBox.scrollTop = messagesBox.scrollHeight;
        } else {
            clearInterval(timer);
            element.innerHTML = htmlFormatted; // render clean final HTML without cursor
            if (callback) callback();
        }
    }, speed);
}

async function handleChipClick(text) {
    const drawer = document.getElementById("mentor-drawer");
    if (drawer && !drawer.classList.contains("active")) {
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

async function loadMentorChatHistory() {
    const messagesBox = document.getElementById("mentor-chat-messages");
    if (!messagesBox) return;
    
    try {
        const response = await fetch("/ai-mentor/history");
        const data = await response.json();
        
        if (response.ok) {
            // Update memory ribbon statistics display
            const memText = document.getElementById("mentor-memory-text");
            if (memText) {
                memText.innerHTML = `Memory: Track: <strong>${data.track}</strong> | XP: <strong>${data.xp}</strong> | Resume: <strong>${data.resume_score}%</strong>`;
            }
            
            if (data.history && data.history.length > 0) {
                messagesBox.innerHTML = "";
                data.history.forEach(h => {
                    const messageClass = h.sender === "user" ? "user" : "mentor";
                    const formattedContent = parseMarkdown(h.content);
                    
                    const msgDiv = document.createElement("div");
                    msgDiv.className = `message ${messageClass}`;
                    
                    const p = document.createElement("p");
                    p.innerHTML = formattedContent;
                    msgDiv.appendChild(p);
                    
                    // Render navigation shortcut cards inside matching history blocks
                    if (h.sender === "ai") {
                        renderRichComponentCards(msgDiv, h.content);
                    }
                    
                    messagesBox.appendChild(msgDiv);
                });
                messagesBox.scrollTop = messagesBox.scrollHeight;
            }
        }
    } catch (e) {
        console.error("Error loading chat history:", e);
    }
}

let lastMentorMessageTime = 0;

async function executeMentorQuery(msg) {
    const now = Date.now();
    if (now - lastMentorMessageTime < 3000) {
        alert("⚠️ Slow down! Please wait at least 3 seconds between messages.");
        return;
    }
    lastMentorMessageTime = now;

    const messagesBox = document.getElementById("mentor-chat-messages");
    if (!messagesBox) return;

    
    // Add user message to UI
    const userDiv = document.createElement("div");
    userDiv.className = "message user";
    userDiv.innerHTML = `<p>${escapeHtml(msg)}</p>`;
    messagesBox.appendChild(userDiv);
    messagesBox.scrollTop = messagesBox.scrollHeight;
    
    // Add thinking spinner placeholder
    const thinkingId = "thinking-" + Date.now();
    const thinkingDiv = document.createElement("div");
    thinkingDiv.className = "message mentor";
    thinkingDiv.id = thinkingId;
    thinkingDiv.innerHTML = `<p><i class="fa-solid fa-spinner fa-spin me-1 text-primary"></i> Advisor is formulating response...</p>`;
    messagesBox.appendChild(thinkingDiv);
    messagesBox.scrollTop = messagesBox.scrollHeight;
    
    const customKey = localStorage.getItem("campusmate_gemini_key") || "";
    
    try {
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || "";
        const response = await fetch("/ai-mentor/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify({ message: msg, custom_key: customKey })
        });
        
        const data = await response.json();
        const placeholder = document.getElementById(thinkingId);
        if (placeholder) placeholder.remove();
        
        if (response.ok && data.success) {
            const aiMsgDiv = document.createElement("div");
            aiMsgDiv.className = "message mentor";
            
            const p = document.createElement("p");
            aiMsgDiv.appendChild(p);
            messagesBox.appendChild(aiMsgDiv);
            messagesBox.scrollTop = messagesBox.scrollHeight;
            
            // Stream output word by word
            streamReplyEffect(p, data.response, () => {
                // Render any navigation shortcards after streaming completes
                renderRichComponentCards(aiMsgDiv, data.response);
                messagesBox.scrollTop = messagesBox.scrollHeight;
                updateSuggestionChips(msg);
            });
        } else {
            messagesBox.innerHTML += `
                <div class="message mentor text-danger">
                    <p>Error getting response: ${data.error || "Unknown response error"}</p>
                </div>
            `;
            messagesBox.scrollTop = messagesBox.scrollHeight;
        }
    } catch (e) {
        console.error(e);
        const placeholder = document.getElementById(thinkingId);
        if (placeholder) placeholder.remove();
        messagesBox.innerHTML += `
            <div class="message mentor text-danger">
                <p>Connection failed. Check server status.</p>
            </div>
        `;
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

// Sync displays on DOM load
document.addEventListener("DOMContentLoaded", () => {
    loadMentorChatHistory();
});
