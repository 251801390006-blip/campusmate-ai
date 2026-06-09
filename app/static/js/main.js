// CampusMate AI Frontend Controller Functions

// Toggle Collapsible Sidebar Drawer (Mobile & Desktop)
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar-drawer");
    const backdrop = document.getElementById("sidebar-backdrop");
    const mainContent = document.querySelector(".main-with-sidebar");
    
    if (window.innerWidth >= 992) {
        if (sidebar && mainContent) {
            sidebar.classList.toggle("collapsed");
            mainContent.classList.toggle("expanded");
            // Store preference in localStorage
            const isCollapsed = sidebar.classList.contains("collapsed");
            localStorage.setItem("sidebar-collapsed", isCollapsed ? "true" : "false");
        }
    } else {
        if (sidebar && backdrop) {
            sidebar.classList.toggle("open");
            backdrop.classList.toggle("open");
        }
    }
}

// Restore sidebar collapse state on page load
document.addEventListener("DOMContentLoaded", () => {
    if (window.innerWidth >= 992) {
        const isCollapsed = localStorage.getItem("sidebar-collapsed") === "true";
        const sidebar = document.getElementById("sidebar-drawer");
        const mainContent = document.querySelector(".main-with-sidebar");
        if (isCollapsed && sidebar && mainContent) {
            sidebar.classList.add("collapsed");
            mainContent.classList.add("expanded");
        }
    }
});

// Toggle Password Field Visibility
function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector("i");
    if (input && icon) {
        if (input.type === "password") {
            input.type = "text";
            icon.className = "fa-solid fa-eye-slash";
        } else {
            input.type = "password";
            icon.className = "fa-solid fa-eye";
        }
    }
}

// Toggle Account Switcher Dropdown (Staging / Testing Bypass)
function toggleSwitcherDropdown(event) {
    event.stopPropagation();
    const menu = document.getElementById("switcher-dropdown-menu");
    if (menu) {
        menu.classList.toggle("hidden");
    }
}

// Close Dropdowns on outside click
window.addEventListener("click", () => {
    const menu = document.getElementById("switcher-dropdown-menu");
    if (menu && !menu.classList.contains("hidden")) {
        menu.classList.add("hidden");
    }
});

// Trigger AJAX Emergency Database Reset (Admin only)
async function triggerDatabaseReset(url, csrfToken) {
    const confirmMessage = "⚠️ WARNING: This will completely WIPE the entire SQLite database, delete all users and feedback records, and re-seed default demo users. Are you sure you want to continue?";
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    const doubleConfirm = prompt("Please type 'RESET' to confirm database deletion:");
    if (doubleConfirm !== "RESET") {
        alert("Database reset canceled. Confirmation word did not match.");
        return;
    }
    
    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            }
        });
        
        const data = await response.json();
        if (response.ok && data.success) {
            alert(data.message);
            window.location.reload();
        } else {
            alert("Error: " + (data.error || "Failed to reset database."));
        }
    } catch (error) {
        console.error("Database reset request failed:", error);
        alert("Connection error: Failed to trigger database control panel reset.");
    }
}

// --- GLOBAL SEARCH & NOTIFICATION MANAGEMENT ---

// Toggle Notification Dropdown
function toggleNotificationDropdown(event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById("notification-dropdown");
    if (dropdown) {
        dropdown.classList.toggle("hidden");
    }
}

// Close dropdowns when clicking outside
window.addEventListener("click", (e) => {
    const dropdown = document.getElementById("notification-dropdown");
    const bellBtn = document.getElementById("notification-bell-btn");
    if (dropdown && !dropdown.classList.contains("hidden")) {
        if (!dropdown.contains(e.target) && (!bellBtn || !bellBtn.contains(e.target))) {
            dropdown.classList.add("hidden");
        }
    }
    
    // Also close search dropdown if clicking outside
    const searchDropdown = document.getElementById("global-search-results");
    const searchInput = document.getElementById("global-search-input");
    if (searchDropdown && !searchDropdown.classList.contains("hidden")) {
        if (!searchDropdown.contains(e.target) && (!searchInput || !searchInput.contains(e.target))) {
            searchDropdown.classList.add("hidden");
        }
    }
});

// Dismiss single notification
async function dismissNotification(event, notifId) {
    if (event) event.stopPropagation();
    const notifItem = document.getElementById(`notif-item-${notifId}`);
    if (!notifItem) return;
    
    notifItem.style.opacity = "0.5";
    notifItem.style.pointerEvents = "none";
    
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || "";
    try {
        const response = await fetch(`/notifications/read/${notifId}`, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken
            }
        });
        
        if (response.ok) {
            notifItem.remove();
            const badge = document.getElementById("notif-badge-count");
            if (badge) {
                let count = parseInt(badge.innerText) - 1;
                if (count > 0) {
                    badge.innerText = count;
                } else {
                    badge.remove();
                    const markAllBtn = document.querySelector(".mark-all-read-btn");
                    if (markAllBtn) markAllBtn.remove();
                    const notifBody = document.getElementById("notif-dropdown-body");
                    if (notifBody) {
                        notifBody.innerHTML = `
                            <div class="notif-empty text-center py-4 text-muted">
                                <i class="fa-regular fa-bell-slash mb-2 d-block" style="font-size: 1.5rem;"></i>
                                <p style="font-size: 0.75rem; margin-bottom: 0;">All caught up! No new notifications.</p>
                            </div>
                        `;
                    }
                }
            }
        } else {
            notifItem.style.opacity = "1";
            notifItem.style.pointerEvents = "auto";
            alert("Failed to dismiss notification.");
        }
    } catch (e) {
        console.error(e);
        notifItem.style.opacity = "1";
        notifItem.style.pointerEvents = "auto";
    }
}

// Mark all read
async function markAllNotificationsRead(event) {
    if (event) event.stopPropagation();
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || "";
    try {
        const response = await fetch("/notifications/read-all", {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken
            }
        });
        
        if (response.ok) {
            const badge = document.getElementById("notif-badge-count");
            if (badge) badge.remove();
            
            const markAllBtn = document.querySelector(".mark-all-read-btn");
            if (markAllBtn) markAllBtn.remove();
            
            const notifBody = document.getElementById("notif-dropdown-body");
            if (notifBody) {
                notifBody.innerHTML = `
                    <div class="notif-empty text-center py-4 text-muted">
                        <i class="fa-regular fa-bell-slash mb-2 d-block" style="font-size: 1.5rem;"></i>
                        <p style="font-size: 0.75rem; margin-bottom: 0;">All caught up! No new notifications.</p>
                    </div>
                `;
            }
        } else {
            alert("Failed to clear notifications.");
        }
    } catch (e) {
        console.error(e);
    }
}

// Live Global Search keyup handler
document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("global-search-input");
    const searchResults = document.getElementById("global-search-results");
    
    if (searchInput && searchResults) {
        let debounceTimer;
        searchInput.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            const query = searchInput.value.trim();
            
            if (query.length < 1) {
                searchResults.innerHTML = "";
                searchResults.classList.add("hidden");
                return;
            }
            
            debounceTimer = setTimeout(async () => {
                try {
                    const response = await fetch(`/global-search?q=${encodeURIComponent(query)}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.results && data.results.length > 0) {
                            searchResults.innerHTML = data.results.map(item => `
                                <a href="${item.url}" class="search-result-item">
                                    <span class="item-title">${escapeHtml(item.title)}</span>
                                    <span class="item-category">${escapeHtml(item.category)}</span>
                                </a>
                            `).join("");
                            searchResults.classList.remove("hidden");
                        } else {
                            searchResults.innerHTML = `
                                <div class="p-3 text-center text-muted" style="font-size: 0.75rem;">
                                    No matching roadmaps or tools found.
                                </div>
                            `;
                            searchResults.classList.remove("hidden");
                        }
                    }
                } catch (e) {
                    console.error("Global search failed:", e);
                }
            }, 200);
        });
        
        searchInput.addEventListener("focus", () => {
            if (searchInput.value.trim().length > 0) {
                searchResults.classList.remove("hidden");
            }
        });
    }
});

// Helper for escaping search result HTML
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

