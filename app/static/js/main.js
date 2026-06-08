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
