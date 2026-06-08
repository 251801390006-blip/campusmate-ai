// CampusMate AI Floating AI Mentor Drawer Controller

function toggleMentorDrawer() {
    const drawer = document.getElementById("mentor-drawer");
    const arrow = document.getElementById("mentor-arrow-icon");
    if (!drawer) return;
    drawer.classList.toggle("active");
    
    if (drawer.classList.contains("active")) {
        if (arrow) arrow.className = "fa-solid fa-chevron-down";
        // Fetch history when drawer opens to ensure sync
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

function typeWriterEffect(element, html, callback) {
    let i = 0;
    const speed = 8; // milliseconds
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
            // Update memory bar
            const memText = document.getElementById("mentor-memory-text");
            if (memText) {
                memText.innerHTML = `Memory: Track: <strong>${data.track}</strong> | XP: <strong>${data.xp}</strong> | Resume: <strong>${data.resume_score}%</strong>`;
            }
            
            if (data.history && data.history.length > 0) {
                messagesBox.innerHTML = "";
                data.history.forEach(h => {
                    const messageClass = h.sender === "user" ? "user" : "mentor";
                    messagesBox.innerHTML += `
                        <div class="message ${messageClass}">
                            <p>${h.content}</p>
                        </div>
                    `;
                });
                messagesBox.scrollTop = messagesBox.scrollHeight;
            }
        }
    } catch (e) {
        console.error("Error loading chat history:", e);
    }
}

async function executeMentorQuery(msg) {
    const messagesBox = document.getElementById("mentor-chat-messages");
    if (!messagesBox) return;
    
    // Add user message to UI
    messagesBox.innerHTML += `
        <div class="message user">
            <p>${escapeHtml(msg)}</p>
        </div>
    `;
    messagesBox.scrollTop = messagesBox.scrollHeight;
    
    // Add thinking placeholder
    const thinkingId = "thinking-" + Date.now();
    messagesBox.innerHTML += `
        <div class="message mentor" id="${thinkingId}">
            <p><i class="fa-solid fa-spinner fa-spin"></i> Coach is thinking...</p>
        </div>
    `;
    messagesBox.scrollTop = messagesBox.scrollHeight;
    
    // Get custom gemini key from local storage if set
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
            const mentorMsgId = "mentor-msg-" + Date.now();
            messagesBox.innerHTML += `
                <div class="message mentor" id="${mentorMsgId}">
                    <p></p>
                </div>
            `;
            messagesBox.scrollTop = messagesBox.scrollHeight;
            
            const targetMsgEl = document.querySelector(`#${mentorMsgId} p`);
            typeWriterEffect(targetMsgEl, data.response, () => {
                messagesBox.scrollTop = messagesBox.scrollHeight;
                updateSuggestionChips(msg);
            });
        } else {
            messagesBox.innerHTML += `
                <div class="message mentor text-danger">
                    <p>Failed to get response: ${data.error || "Unknown error"}</p>
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
                <p>Connection failed. Please check network settings.</p>
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

// Initial history fetch on load
document.addEventListener("DOMContentLoaded", () => {
    loadMentorChatHistory();
});
