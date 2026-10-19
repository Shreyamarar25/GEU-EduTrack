const auth = getAuth();
if (!auth.token) window.location.href = "index.html";

// Which pages each role can open (matches the "Relevant diagrams" feature table)
const MENUS = {
  ADMIN:    ["overview", "students", "teachers", "courses", "enrollments", "attendance", "marks", "reports", "scheduler"],
  TEACHER:  ["overview", "courses", "attendance", "marks", "reports"],
  STUDENT:  ["overview", "courses", "attendance", "marks", "reports"],
  EXAMCELL: ["overview", "marks", "reports"],
};
const LABELS = { overview: "Overview", students: "Students", teachers: "Teachers", courses: "Courses",
  enrollments: "Enrollment", attendance: "Attendance", marks: "Marks", reports: "Reports", scheduler: "OS Scheduler" };

document.getElementById("who").textContent = `${auth.name} (${auth.role})`;
document.getElementById("logoutBtn").onclick = logout;

const menu = document.getElementById("menu");
const page = document.getElementById("page");
const items = MENUS[auth.role] || ["overview"];

async function show(name) {
  menu.querySelectorAll("a").forEach(a => a.classList.toggle("active", a.dataset.page === name));
  sessionStorage.setItem("page", name);  // remember which page is open
  page.innerHTML = "<p>Loading...</p>";
  try { await PAGES[name](page); }
  catch (e) { page.innerHTML = `<div class="msg err">${esc(e.message)}</div>`; }
}

menu.innerHTML = items.map(n => `<a data-page="${n}">${LABELS[n]}</a>`).join("");
menu.querySelectorAll("a").forEach(a => a.onclick = () => show(a.dataset.page));

// Open the page you were last on (only if your role may see it), otherwise Overview
const saved = sessionStorage.getItem("page");
show(items.includes(saved) ? saved : "overview");