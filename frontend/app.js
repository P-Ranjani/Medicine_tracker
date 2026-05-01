const API_BASE = "http://127.0.0.1:5000";

let currentUser = null; // { id, name, email, role }

function setCurrentUser(user) {
  currentUser = user;
  const label = document.getElementById("currentUserLabel");
  const logoutBtn = document.getElementById("logoutBtn");
  const authSection = document.getElementById("authSection");
  const patientSection = document.getElementById("patientSection");
  const caregiverStatus = document.getElementById("caregiverStatus");

  if (!user) {
    label.textContent = "Not signed in";
    logoutBtn.classList.add("hidden");
    authSection.classList.remove("hidden");
    patientSection.classList.add("hidden");
    caregiverStatus.textContent = "Role: –";
    caregiverStatus.className = "status-pill";
    return;
  }

  label.textContent = `${user.name} · ${user.email} (${user.role})`;
  logoutBtn.classList.remove("hidden");
  authSection.classList.add("hidden");

  if (user.role === "patient") {
    patientSection.classList.remove("hidden");
  } else {
    patientSection.classList.add("hidden");
  }

  if (user.role === "caregiver") {
    caregiverStatus.textContent = "Role: Caregiver";
    caregiverStatus.className = "status-pill good";
  } else if (user.role === "patient") {
    caregiverStatus.textContent = "Role: Patient";
    caregiverStatus.className = "status-pill";
  } else {
    caregiverStatus.textContent = "Role: –";
    caregiverStatus.className = "status-pill";
  }
}

async function apiRequest(path, options = {}) {
  const headers = options.headers || {};
  if (currentUser && currentUser.id) {
    headers["X-User-Id"] = String(currentUser.id);
  }
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const res = await fetch(API_BASE + path, {
    ...options,
    headers,
  });

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!res.ok) {
    const msg = data && data.error ? data.error : `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

function wireAuth() {
  const roleToggle = document.getElementById("roleToggle");
  const caregiverLinkFields = document.getElementById("caregiverLinkFields");
  const registerBtn = document.getElementById("registerBtn");
  const authError = document.getElementById("authError");
  const loginBtn = document.getElementById("loginBtn");
  const loginError = document.getElementById("loginError");
  const logoutBtn = document.getElementById("logoutBtn");

  let selectedRole = "patient";

  roleToggle.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-role]");
    if (!btn) return;
    selectedRole = btn.dataset.role;
    [...roleToggle.querySelectorAll("button")].forEach((b) =>
      b.classList.toggle("active", b === btn)
    );
    if (selectedRole === "patient") {
      caregiverLinkFields.classList.remove("hidden");
    } else {
      caregiverLinkFields.classList.add("hidden");
    }
  });

  registerBtn.addEventListener("click", async () => {
    authError.textContent = "";
    const name = document.getElementById("regName").value.trim();
    const email = document.getElementById("regEmail").value.trim();
    const password = document.getElementById("regPassword").value;
    const caregiverEmail = document.getElementById("caregiverEmail").value.trim();
    const relationship = document.getElementById("relationship").value.trim();

    if (!name || !email || !password) {
      authError.textContent = "Name, email and password are required.";
      return;
    }
    try {
      const body = {
        name,
        email,
        password,
        role: selectedRole,
      };
      if (selectedRole === "patient" && caregiverEmail) {
        body.caregiver_email = caregiverEmail;
        if (relationship) body.relationship = relationship;
      }
      const data = await apiRequest("/api/register", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setCurrentUser(data.user);
      document.getElementById("loginEmail").value = email;
      document.getElementById("loginPassword").value = password;
      await refreshMedications();
      await refreshAdherenceSummary();
    } catch (err) {
      authError.textContent = err.message || "Registration failed.";
    }
  });

  loginBtn.addEventListener("click", async () => {
    loginError.textContent = "";
    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;
    if (!email || !password) {
      loginError.textContent = "Email and password are required.";
      return;
    }
    try {
      const data = await apiRequest("/api/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      // server returns token as string(user.id)
      const user = data.user;
      setCurrentUser(user);
      await refreshMedications();
      await refreshAdherenceSummary();
    } catch (err) {
      loginError.textContent = err.message || "Login failed.";
    }
  });

  logoutBtn.addEventListener("click", () => {
    setCurrentUser(null);
  });
}

async function refreshMedications() {
  const container = document.getElementById("medicationList");
  if (!currentUser || currentUser.role !== "patient") {
    container.textContent = "Log in as a patient to see medications.";
    return;
  }
  try {
    const data = await apiRequest("/api/medications");
    const meds = data.medications || [];
    if (!meds.length) {
      container.textContent = "No medications saved yet.";
      return;
    }
    const fragments = meds
      .map((m) => {
        const dates =
          (m.start_date || m.end_date) &&
          ` · ${m.start_date || ""}${m.end_date ? " → " + m.end_date : ""}`;
        return `
          <div style="margin-bottom: 4px;">
            <strong>${m.medicine_name}</strong> ${m.dosage || ""} · <span class="tag">${m.schedule_time}</span>${dates || ""}
            <div class="pill-list">
              <button class="btn small secondary" data-adherence="taken" data-med-id="${m.id}">Taken</button>
              <button class="btn small secondary" data-adherence="missed" data-med-id="${m.id}">Missed</button>
              <button class="btn small secondary" data-adherence="skipped" data-med-id="${m.id}">Skipped</button>
            </div>
          </div>
        `;
      })
      .join("");
    container.innerHTML = fragments;
    container.classList.remove("muted");

    container.querySelectorAll("button[data-adherence]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const status = btn.getAttribute("data-adherence");
        const medId = Number(btn.getAttribute("data-med-id"));
        try {
          await apiRequest("/api/adherence", {
            method: "POST",
            body: JSON.stringify({ medication_id: medId, status }),
          });
          await refreshAdherenceSummary();
        } catch (err) {
          alert("Failed to record adherence: " + err.message);
        }
      });
    });
  } catch (err) {
    container.textContent = "Failed to load medications: " + err.message;
  }
}

async function refreshAdherenceSummary() {
  const box = document.getElementById("adherenceSummary");
  if (!currentUser || currentUser.role !== "patient") {
    box.textContent = "Log in as a patient to view adherence.";
    box.classList.remove("hidden");
    return;
  }
  try {
    const data = await apiRequest("/api/adherence/summary");
    const rows = data.summary || [];
    if (!rows.length) {
      box.textContent = "No adherence records yet. Mark doses as taken/missed to see analytics.";
      box.classList.remove("hidden");
      return;
    }
    const text = rows
      .map(
        (r) =>
          `${r.medication}: ${r.taken}/${r.total} taken (${r.adherence_pct}% adherence), missed ${r.missed}`
      )
      .join("\n");
    box.textContent = text;
    box.classList.remove("hidden");
  } catch (err) {
    box.textContent = "Failed to load adherence summary: " + err.message;
    box.classList.remove("hidden");
  }
}

function wirePatientFeatures() {
  const uploadBtn = document.getElementById("uploadPrescriptionBtn");
  const ocrResult = document.getElementById("ocrResult");
  const addMedBtn = document.getElementById("addMedBtn");
  const refreshSummaryBtn = document.getElementById("refreshSummaryBtn");

  uploadBtn.addEventListener("click", async () => {
    if (!currentUser || currentUser.role !== "patient") {
      alert("Log in as a patient first.");
      return;
    }
    const fileInput = document.getElementById("prescriptionFile");
    const file = fileInput.files[0];
    if (!file) {
      alert("Choose an image file first.");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    ocrResult.textContent = "Scanning prescription...";
    ocrResult.classList.remove("hidden");
    try {
      const data = await apiRequest("/api/ocr/scan", {
        method: "POST",
        body: formData,
      });
      const meds = (data.parsed_medications || [])
        .map(
          (m) =>
            `- ${m.medicine_name} ${m.dosage || ""} (${m.schedule_text || "schedule not parsed"})`
        )
        .join("\n");
      ocrResult.textContent =
        "Raw text:\n" + data.raw_text + "\n\nParsed medications:\n" + (meds || "None");
    } catch (err) {
      ocrResult.textContent = "Failed to scan prescription: " + err.message;
    }
  });

  addMedBtn.addEventListener("click", async () => {
    if (!currentUser || currentUser.role !== "patient") {
      alert("Log in as a patient first.");
      return;
    }
    const name = document.getElementById("medName").value.trim();
    const dose = document.getElementById("medDose").value.trim();
    const timeVal = document.getElementById("medTime").value;
    const start = document.getElementById("medStart").value;
    const end = document.getElementById("medEnd").value;

    if (!name || !timeVal) {
      alert("Medicine name and time are required.");
      return;
    }
    const payload = {
      medications: [
        {
          medicine_name: name,
          dosage: dose || null,
          schedule_time: timeVal,
          start_date: start || null,
          end_date: end || null,
        },
      ],
    };
    try {
      await apiRequest("/api/medications", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await refreshMedications();
      document.getElementById("medName").value = "";
      document.getElementById("medDose").value = "";
    } catch (err) {
      alert("Failed to save medication: " + err.message);
    }
  });

  refreshSummaryBtn.addEventListener("click", () => {
    refreshAdherenceSummary();
  });
}

function wireChatbotAndInteractions() {
  const askBtn = document.getElementById("askChatbotBtn");
  const chatQuestion = document.getElementById("chatQuestion");
  const chatbotAnswer = document.getElementById("chatbotAnswer");

  askBtn.addEventListener("click", async () => {
    if (!currentUser) {
      alert("Log in first to use the chatbot.");
      return;
    }
    const q = chatQuestion.value.trim();
    if (!q) {
      alert("Type a question first.");
      return;
    }
    chatbotAnswer.textContent = "Thinking...";
    chatbotAnswer.classList.remove("hidden");
    try {
      const data = await apiRequest("/api/chatbot", {
        method: "POST",
        body: JSON.stringify({ question: q }),
      });
      chatbotAnswer.textContent = data.answer || "(No answer returned.)";
    } catch (err) {
      chatbotAnswer.textContent = "Chatbot error: " + err.message;
    }
  });

  const checkBtn = document.getElementById("checkInteractionsBtn");
  const interactionInput = document.getElementById("interactionMeds");
  const interactionResults = document.getElementById("interactionResults");

  checkBtn.addEventListener("click", async () => {
    if (!currentUser) {
      alert("Log in first.");
      return;
    }
    const raw = interactionInput.value.trim();
    if (!raw) {
      alert("Enter at least one medicine name.");
      return;
    }
    const meds = raw.split(",").map((m) => m.trim());
    interactionResults.textContent = "Checking interactions...";
    interactionResults.classList.remove("hidden");
    try {
      const data = await apiRequest("/api/drug/interactions", {
        method: "POST",
        body: JSON.stringify({ medicines: meds }),
      });
      const results = data.interactions || [];
      if (!results.length) {
        interactionResults.textContent =
          "No interaction information returned. This does not guarantee safety. Always consult a healthcare professional.";
        return;
      }
      const text = results
        .map(
          (r) =>
            `${r.medicine}:\n${(r.raw_interaction_info || []).join(
              "\n"
            )}\n\nNote: ${r.note}`
        )
        .join("\n\n---\n\n");
      interactionResults.textContent = text;
    } catch (err) {
      interactionResults.textContent = "Failed to check interactions: " + err.message;
    }
  });
}

function wireCaregiverDashboard() {
  const btn = document.getElementById("loadPatientsBtn");
  const box = document.getElementById("caregiverPatients");

  btn.addEventListener("click", async () => {
    if (!currentUser || currentUser.role !== "caregiver") {
      box.textContent = "Log in as a caregiver account to view linked patients.";
      box.classList.remove("hidden");
      return;
    }
    box.textContent = "Loading patients...";
    box.classList.remove("hidden");
    try {
      const data = await apiRequest("/api/caregiver/patients");
      const patients = data.patients || [];
      if (!patients.length) {
        box.textContent = "No linked patients yet.";
        return;
      }
      const text = patients
        .map((p) => {
          const meds = p.medications || [];
          const medLines = meds.length
            ? meds
                .map(
                  (m) =>
                    `  - ${m.medicine_name} ${m.dosage || ""} at ${m.schedule_time}${
                      m.start_date ? ` (from ${m.start_date}` : ""
                    }${m.end_date ? ` to ${m.end_date})` : m.start_date ? ")" : ""}`
                )
                .join("\n")
            : "  (no medications)";
          return `Patient: ${p.patient.name} (${p.patient.email})\n${medLines}`;
        })
        .join("\n\n---\n\n");
      box.textContent = text;
    } catch (err) {
      box.textContent = "Failed to load patients: " + err.message;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setCurrentUser(null);
  wireAuth();
  wirePatientFeatures();
  wireChatbotAndInteractions();
  wireCaregiverDashboard();
});

