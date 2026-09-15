// =========================================================
// e-KHARID SHARED SCRIPT
// Backend-integrated + shared helpers
// =========================================================

const API_BASE_URL = "/api";

async function apiRequest(path, options = {}) {
    const response = await fetch(API_BASE_URL + path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || "Something went wrong. Please try again.");
    }

    return data;
}

function apiGet(path) {
    return apiRequest(path, { method: "GET" });
}

function apiPost(path, body) {
    return apiRequest(path, {
        method: "POST",
        body: JSON.stringify(body)
    });
}

function showMessage(containerEl, text, type = "error") {
    if (containerEl) {
        containerEl.innerHTML = `<div class="message ${type}">${text}</div>`;
    }
}

function clearMessage(containerEl) {
    if (containerEl) containerEl.innerHTML = "";
}

// =========================================================
// STAGES
// =========================================================

const STAGES = [
    { key: "NOT_ARRIVED", label: "Not Arrived" },
    { key: "ARRIVED", label: "Arrived" },
    { key: "QUALITY", label: "Quality" },
    { key: "WEIGHT", label: "Weight" },
    { key: "STORAGE", label: "Storage" },
    { key: "PAYMENT", label: "Payment" },
    { key: "COMPLETED", label: "Completed" }
];

function stageLabel(stageKey) {
    const found = STAGES.find(s => s.key === stageKey);
    return found ? found.label : stageKey;
}

function stageBadgeHtml(stageKey) {
    return `<span class="badge">${stageLabel(stageKey)}</span>`;
}

// =========================================================
// SESSION HELPERS
// =========================================================

function saveFarmerSession(farmer) {
    localStorage.setItem("farmer", JSON.stringify(farmer));
    localStorage.setItem("ekharidFarmerId", farmer.farmer_id);
    localStorage.setItem("ekharidUserName", farmer.name);
    localStorage.setItem("ekharidMobile", farmer.mobile);
    localStorage.setItem("ekharidRole", "Farmer / कृषि");
    localStorage.setItem("ekharidLoggedIn", "true");
}

function getFarmerSession() {
    const raw = localStorage.getItem("farmer");
    if (raw) {
        try { return JSON.parse(raw); } catch (_) {}
    }

    const id = localStorage.getItem("ekharidFarmerId");
    const name = localStorage.getItem("ekharidUserName");
    const mobile = localStorage.getItem("ekharidMobile");

    return id ? { farmer_id: id, name: name || "Farmer", mobile: mobile || "" } : null;
}

function saveOfficerSession(officer) {
    localStorage.setItem("officer", JSON.stringify(officer));
    localStorage.setItem("ekharidOfficerId", officer.officer_id || officer.username || "officer");
    localStorage.setItem("ekharidOfficerName", officer.name || officer.username || "Official");
    localStorage.setItem("ekharidRole", "Officials");
    localStorage.setItem("ekharidLoggedIn", "true");
}

function getOfficerSession() {
    const raw = localStorage.getItem("officer");
    if (raw) {
        try { return JSON.parse(raw); } catch (_) {}
    }
    return null;
}

function requireFarmerLogin() {
    const farmer = getFarmerSession();
    if (!farmer) {
        window.location.href = "index.html";
        return null;
    }
    return farmer;
}

function requireOfficerLogin() {
    const officer = getOfficerSession();
    if (!officer) {
        window.location.href = "index.html";
        return null;
    }
    return officer;
}

function getUserName() {
    return localStorage.getItem("ekharidUserName") || "Farmer";
}

function getUserRole() {
    return localStorage.getItem("ekharidRole") || "Farmer / कृषि";
}

function getFarmerId() {
    return localStorage.getItem("ekharidFarmerId") || "";
}

function loadUserName() {
    const name = getUserName();
    const role = getUserRole();

    document.querySelectorAll(".user-name").forEach(el => el.textContent = name);
    document.querySelectorAll(".user-role").forEach(el => el.textContent = role);

    const gatePassName = document.getElementById("name");
    if (gatePassName && !gatePassName.value) gatePassName.value = name;

    const phone = document.getElementById("phone");
    const farmer = getFarmerSession();
    if (phone && farmer && !phone.value) phone.value = farmer.mobile || "";
}

function clearSessions() {
    [
        "farmer", "officer", "ekharidFarmerId", "ekharidUserName",
        "ekharidMobile", "ekharidRole", "ekharidLoggedIn",
        "ekharidOfficerId", "ekharidOfficerName"
    ].forEach(key => localStorage.removeItem(key));
}

function handleLogout() {
    clearSessions();
    window.location.href = "index.html";
}

function logout() {
    handleLogout();
}

// =========================================================
// LOGIN MODAL
// =========================================================

function openLogin(role) {
    const selectedRole = document.getElementById("selectedRole");
    const modal = document.getElementById("loginModal");
    const secretLabel = document.getElementById("loginSecretLabel");
    const secretInput = document.getElementById("mobile");

    if (selectedRole) selectedRole.textContent = role;

    if (secretLabel && secretInput) {
        if (role === "Officials") {
            secretLabel.textContent = "Password";
            secretInput.type = "password";
            secretInput.placeholder = "Enter password";
        } else {
            secretLabel.textContent = "Mobile Number";
            secretInput.type = "tel";
            secretInput.placeholder = "Enter mobile number";
        }
    }

    if (modal) modal.classList.add("show");
}

function closeLogin() {
    const modal = document.getElementById("loginModal");
    if (modal) modal.classList.remove("show");
}

async function handleLoginSubmit(event) {
    event.preventDefault();

    const name = document.getElementById("username")?.value.trim() || "";
    const mobile = document.getElementById("mobile")?.value.trim() || "";
    const role = document.getElementById("selectedRole")?.textContent.trim() || "Farmer / कृषि";

    try {
        if (role === "Officials") {
            const username = name;
            const password = mobile;

            if (!username || !password) {
                alert("Please enter username and password.");
                return;
            }

            const data = await apiPost("/officer/login", { username, password });
            saveOfficerSession(data.officer);
            closeLogin();
            window.location.href = "official.html";
            return;
        }

        if (!name || !mobile) {
            alert("Please enter your name and mobile number.");
            return;
        }

        const data = await apiPost("/farmer/login", { name, mobile });
        saveFarmerSession(data.farmer);
        closeLogin();
        loadUserName();
        await loadFarmerPassesAndQueue();

    } catch (error) {
        console.error("Login error:", error);
        alert(error.message || "Login failed.");
    }
}

// =========================================================
// SIDEBAR NAVIGATION
// =========================================================

function showMessageSection(section, button) {
    if (button) {
        document.querySelectorAll(".menu-item").forEach(item => item.classList.remove("active"));
        button.classList.add("active");
    }

    const pages = {
        "Dashboard": "index.html",
        "Live Queue": "queue.html",
        "Payment": "payment.html",
        "Gate Pass": "gatepass.html",
        "Profile": "profile.html",
        "Contact Us": "contact.html"
    };

    if (pages[section]) window.location.href = pages[section];
}

// Keep old function name working too.
function showMessageSectionOld(section, button) {
    showMessageSection(section, button);
}

// =========================================================
// GATE PASS
// =========================================================

async function submitGatePass(event) {
    if (event) event.preventDefault();

    const farmer = getFarmerSession();
    const farmerId = getFarmerId() || farmer?.farmer_id;

    if (!farmerId) {
        alert("Please login as a farmer first.");
        window.location.href = "index.html";
        return;
    }

    const get = id => document.getElementById(id)?.value || "";

    const payload = {
        farmer_id: farmerId,
        crop_type: get("cropType"),
        crop_name: get("cropName"),
        mandi: get("mandi"),
        vehicle_number: get("vehicleNumber"),
        vehicle_type: get("vehicleType"),
        desired_date: get("desiredDate"),
        estimated_weight: parseFloat(get("estimatedWeight"))
    };

    try {
        const data = await apiPost("/gate-pass", payload);

        const success = document.getElementById("successMessage");
        if (success) {
            success.classList.add("show");
            success.scrollIntoView({ behavior: "smooth", block: "center" });
        }

        alert(`Gate Pass Generated Successfully! ID: ${data.gate_pass_id}`);
        await loadFarmerPassesAndQueue();

    } catch (error) {
        alert(error.message || "Failed to create gate pass.");
    }
}

// Original HTML function name compatibility.
function handleGatePassSubmit(event) {
    return submitGatePass(event);
}

// =========================================================
// FARMER PASSES ON DASHBOARD
// =========================================================

async function loadFarmerPassesAndQueue() {
    const container = document.getElementById("passesContainer");
    const farmerId = getFarmerId();

    if (!container || !farmerId) return;

    try {
        const passes = await apiGet(`/farmer/passes/${farmerId}`);
        const queue = await apiGet(`/queue/farmer/${farmerId}`).catch(() => ({}));

        if (!passes.length) {
            container.innerHTML = `<p>No active gate passes found. Generate a gate pass to see your queue.</p>`;
            return;
        }

        container.innerHTML = "";

        for (const pass of passes) {
            const card = document.createElement("div");
            card.className = "gate-pass-card";
            const isLatest = pass.gate_pass_id === queue.gate_pass_id;
            card.innerHTML = `
                <div class="pass-header">
                    <h4>Gate Pass: ${pass.gate_pass_id}</h4>
                    <span class="badge">${isLatest ? stageLabel(queue.stage) : pass.status}</span>
                </div>
                <div class="pass-details">
                    <p><strong>Crop:</strong> ${pass.crop_name}</p>
                    <p><strong>Quantity:</strong> ${pass.estimated_weight} Quintals</p>
                    <p><strong>Mandi:</strong> ${pass.mandi}</p>
                    <p><strong>Date:</strong> ${pass.desired_date}</p>
                    ${isLatest ? `<p><strong>Farmers Ahead:</strong> ${queue.farmers_ahead ?? 0}</p>` : ""}
                </div>
            `;
            container.appendChild(card);
        }

    } catch (error) {
        console.error("Error loading passes and queue:", error);
    }
}

// =========================================================
// INIT
// =========================================================

document.addEventListener("DOMContentLoaded", function () {
    loadUserName();
    loadFarmerPassesAndQueue();
});

window.addEventListener("click", function (event) {
    const modal = document.getElementById("loginModal");
    if (modal && event.target === modal) closeLogin();
});
