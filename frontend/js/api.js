// Shared helpers: talk to the Django API and keep the login token.
const API = "http://127.0.0.1:8000/api";

function getAuth() {
  return { token: localStorage.getItem("token"), role: localStorage.getItem("role"), name: localStorage.getItem("name") };
}

function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}

// Turns Django's error JSON into one readable line
function errorText(data) {
  if (!data) return "Something went wrong.";
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  return Object.entries(data)
    .map(([k, v]) => (k === "non_field_errors" ? "" : k + ": ") + (Array.isArray(v) ? v.join(" ") : v))
    .join(" | ");
}

async function api(path, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  const { token } = getAuth();
  if (token) headers["Authorization"] = "Token " + token;

  let res;
  try {
    res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : null });
  } catch (e) {
    throw new Error("Cannot reach the backend. Is `python manage.py runserver` running?");
  }
  if (res.status === 401) { logout(); return; }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorText(data));
  return data;
}

// Escape text before putting it into innerHTML
function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function downloadPdf(path, fallbackName = "report.pdf") {
  const { token } = getAuth();
  let res;
  try {
    res = await fetch(API + path, { headers: { Authorization: "Token " + token } });
  } catch (e) {
    throw new Error("Cannot reach the backend. Is `python manage.py runserver` running?");
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(errorText(data));
  }
  const blob = await res.blob();
  const match = /filename="?([^";]+)"?/.exec(res.headers.get("Content-Disposition") || "");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = match ? match[1] : fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

// Asks for a report. Admin gets the PDF straight away; everyone else gets a queued request.
// kind = "attendance" | "performance" | "student"
async function requestReport(kind, studentId = null) {
  const { token } = getAuth();
  let res;
  try {
    res = await fetch(API + "/reports/request/", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Token " + token },
      body: JSON.stringify({ kind: kind, student_id: studentId }),
    });
  } catch (e) {
    throw new Error("Cannot reach the backend. Is `python manage.py runserver` running?");
  }
  if (res.status === 401) { logout(); return; }

  // Admin: the backend sent the PDF itself, so save it
  if ((res.headers.get("Content-Type") || "").includes("application/pdf")) {
    const blob = await res.blob();
    const match = /filename="?([^";]+)"?/.exec(res.headers.get("Content-Disposition") || "");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = match ? match[1] : "report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(link.href);
    return { instant: true };
  }

  // Everyone else: the request was queued
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorText(data));
  return { instant: false, request: data };
}

// Download a report that the Admin has approved
function downloadApproved(processId) {
  return downloadPdf("/reports/requests/" + processId + "/download/");
}