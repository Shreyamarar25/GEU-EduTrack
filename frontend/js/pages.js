// All page renderers. Each one receives the <main> element and fills it.

const today = () => new Date().toISOString().slice(0, 10);

function notify(el, text, ok = false) {
  el.innerHTML = text ? `<div class="msg ${ok ? "ok" : "err"}">${esc(text)}</div>` : "";
}

function buildTable(columns, rows, actions) {
  if (!rows.length) return '<div class="empty">No records found.</div>';
  const head = columns.map(c => `<th>${esc(c.label)}</th>`).join("") + (actions ? "<th></th>" : "");
  const body = rows.map((r, i) =>
    "<tr>" + columns.map(c => {
      const v = c.fmt ? c.fmt(r) : esc(r[c.key] ?? "-");
      return `<td>${v}</td>`;
    }).join("") + (actions ? `<td class="row-actions">${actions(r, i)}</td>` : "") + "</tr>").join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function openModal(title, bodyHtml, onClose) {
  const wrap = document.createElement("div");
  wrap.className = "modal-backdrop";
  wrap.innerHTML = `<div class="modal" role="dialog" aria-modal="true">
    <div class="modal-head"><h3>${esc(title)}</h3>
      <button class="icon-btn" data-close aria-label="Close">&times;</button></div>
    <div class="modal-body">${bodyHtml}</div></div>`;
  const onKey = e => { if (e.key === "Escape") close(); };
  const close = () => {
    wrap.remove();
    document.removeEventListener("keydown", onKey);
    if (onClose) onClose();
  };
  wrap.addEventListener("click", e => {
    if (e.target === wrap || e.target.hasAttribute("data-close")) close();
  });
  document.addEventListener("keydown", onKey);
  document.body.appendChild(wrap);
  return { el: wrap.querySelector(".modal-body"), close };
}

function confirmDialog(title, message, confirmLabel = "Delete") {
  return new Promise(resolve => {
    const { el, close } = openModal(title, `<p>${esc(message)}</p>
      <div class="modal-actions">
        <button class="secondary" data-close>Cancel</button>
        <button class="danger" data-yes>${esc(confirmLabel)}</button></div>`, () => resolve(false));
    el.querySelector("[data-yes]").onclick = () => { resolve(true); close(); };
  });
}

/* ------------------------------------------------------------------
   Generic list + add-form page (used by students, teachers, courses,
   enrollments and marks)
------------------------------------------------------------------- */
async function crudPage(el, cfg) {
  const role = getAuth().role;
  const canWrite = cfg.writeRoles.includes(role);
  const fields = [];
  if (canWrite) {
    for (const f of cfg.fields) {
      const copy = { ...f };
      if (f.from) {
        const list = await api(f.from);
        copy.options = list.map(x => ({ value: typeof f.value === "function" ? f.value(x) : x[f.value], label: f.text(x) }));
      }
      fields.push(copy);
    }
  }

    const formHtml = `<form id="addForm" class="grid">
      ${fields.map(f => `<div><label>${f.label}</label>${
        f.options
          ? `<select name="${f.name}" required>${f.options.map(o => `<option value="${esc(o.value)}">${esc(o.text ?? o.label)}</option>`).join("")}</select>`
          : `<input name="${f.name}" type="${f.type || "text"}" ${f.required === false ? "" : "required"} ${f.value0 ? `value="${f.value0}"` : ""}>`
      }</div>`).join("")}
      <div class="form-actions" style="grid-column:1/-1">
        <button type="button" class="secondary" data-close>Cancel</button>
        <button type="submit">Save</button></div>
    </form><div id="formMsg"></div>`;

  el.innerHTML = `<div class="page-head"><h2>${cfg.title}</h2>
      ${canWrite ? '<button id="openAdd">+ Add new</button>' : ""}</div>
       ${cfg.search ? '<div class="toolbar"><input id="q" placeholder="Search..."></div>' : ""}
    <div id="msg"></div><div id="list"></div>`;

  const msg = el.querySelector("#msg");

  async function load() {
    const q = cfg.search ? el.querySelector("#q").value.trim() : "";
    const rows = await api(cfg.path + (q ? "?search=" + encodeURIComponent(q) : ""));
    const actions = (canWrite && (cfg.deletable !== false || cfg.editField)) || cfg.pdfPath
      ? (r, i) => (cfg.pdfPath ? `<button class="secondary" data-pdf="${i}">PDF report</button>` : "") +
                  (cfg.editField && canWrite ? `<a href="#" data-edit="${i}">Edit ${cfg.editField}</a>` : "") +
                  (cfg.deletable !== false && canWrite ? `<button class="danger" data-del="${i}">Delete</button>` : "")
      : null;
    el.querySelector("#list").innerHTML = buildTable(cfg.columns, rows, actions);

    el.querySelectorAll("[data-pdf]").forEach(b => b.onclick = async () => {
            try {
        const res = await requestReport("student", rows[b.dataset.pdf].student_id);
        notify(msg, res.instant ? "PDF downloaded." : "Request sent. It is waiting for the Admin's approval.", true);
      }
      catch (e) { notify(msg, e.message); }
    });
       el.querySelectorAll("[data-del]").forEach(b => b.onclick = async () => {
     const ok = await confirmDialog("Delete this record?",
       cfg.deleteWarning || "This can't be undone. Related records may be removed too.");
     if (!ok) return;
     try { await api(cfg.path + rows[b.dataset.del][cfg.idKey] + "/", "DELETE"); load(); }
     catch (e) { notify(msg, e.message); }
   });
        el.querySelectorAll("[data-edit]").forEach(a => a.onclick = ev => {
      ev.preventDefault();
      const r = rows[a.dataset.edit];
      const modal = openModal("Edit " + cfg.editField,
        `<form id="editForm">
           <label>New ${esc(cfg.editField)} for ${esc(r.student_name)}</label>
           <input name="v" value="${esc(r[cfg.editField])}" required>
           <div class="form-actions">
             <button type="button" class="secondary" data-close>Cancel</button>
             <button type="submit">Save</button>
           </div>
         </form><div id="editMsg"></div>`);
      modal.el.querySelector("#editForm").onsubmit = async e2 => {
        e2.preventDefault();
        const val = new FormData(e2.target).get("v");
        try {
          await api(cfg.path + r[cfg.idKey] + "/", "PATCH", { [cfg.editField]: val });
          modal.close();
          notify(msg, "Updated.", true);
          load();
        } catch (err) { notify(modal.el.querySelector("#editMsg"), err.message); }
      };
    });
  }

    if (canWrite) {
    el.querySelector("#openAdd").onclick = () => {
      const modal = openModal("Add new", formHtml);
      modal.el.querySelector("#addForm").onsubmit = async ev => {
        ev.preventDefault();
        const formMsg = modal.el.querySelector("#formMsg");
        let body = {};
        new FormData(ev.target).forEach((v, k) => { if (v !== "") body[k] = v; });
        if (cfg.beforeSubmit) body = cfg.beforeSubmit(body);
        try {
          await api(cfg.path, "POST", body);
          modal.close();
          notify(msg, "Saved.", true);
          load();
        } catch (e) { notify(formMsg, e.message); }
      };
    };
  }
     if (cfg.search) {
     let timer;
     el.querySelector("#q").oninput = () => {
       clearTimeout(timer);
       timer = setTimeout(() => load().catch(e => notify(msg, e.message)), 300);
     };
   }
  try { await load(); } catch (e) { notify(msg, e.message); }
}

/* ------------------------------------------------------------------ pages */
const PAGES = {};

const daysFromNow = n => { const d = new Date(); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };

// Edit this list to change the events. Dates below are "days from today" so they always stay upcoming.
const EVENTS = [
  { title: "Tech Fest 2026 - Inauguration", date: daysFromNow(3),  time: "10:00 AM", venue: "Main Auditorium" },
  { title: "Guest Lecture: Cloud Computing",  date: daysFromNow(5),  time: "2:00 PM",  venue: "Seminar Hall" },
  { title: "Hackathon Kick-off",              date: daysFromNow(8),  time: "9:00 AM",  venue: "Computer Lab 2" },
  { title: "Placement Preparation Workshop",  date: daysFromNow(12), time: "11:00 AM", venue: "Btech Block, Lt-12" },
  { title: "Inter-College Sports Meet",       date: daysFromNow(15), time: "8:30 AM",  venue: "CSIT Open Audi" },
  { title: "Cultural Night",                  date: daysFromNow(20), time: "5:30 PM",  venue: "Btech Audi" },
  { title: "Mid-Term Exam Orientation",       date: daysFromNow(24), time: "10:30 AM", venue: "Main Ground" },
];

function eventsPanel() {
  const upcoming = EVENTS.filter(e => e.date >= today()).sort((a, b) => a.date.localeCompare(b.date));
  if (!upcoming.length) return `<div class="panel"><h3>Upcoming events</h3><div class="empty">No upcoming events right now.</div></div>`;
  const fmtDate = d => new Date(d + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  const rows = upcoming.map(e =>
    `<tr><td>${fmtDate(e.date)}</td><td>${esc(e.title)}</td><td>${esc(e.time)}</td><td>${esc(e.venue)}</td></tr>`).join("");
  const moving = upcoming.length > 4;
  return `<div class="panel"><h3>Upcoming events</h3>
    <table class="ev-head"><thead><tr><th>Date</th><th>Event</th><th>Time</th><th>Venue</th></tr></thead></table>
    <div class="ev-view"><table class="ev-body ${moving ? "moving" : ""}"><tbody>${rows}${moving ? rows : ""}</tbody></table></div></div>`;
}

PAGES.overview = async el => {
  const data = await api("/stats/");
  const auth = getAuth();
  const targets = { students: "students", teachers: "teachers", courses: "courses",
                    enrollments: "enrollments", marks: "marks", attendance: "attendance" };
  const actions = {
    ADMIN:    [["Manage students", "students"], ["Mark attendance", "attendance"], ["Run scheduler", "scheduler"], ["View reports", "reports"]],
    TEACHER:  [["Mark attendance", "attendance"], ["Enter marks", "marks"], ["View reports", "reports"]],
    STUDENT:  [["My attendance", "attendance"], ["My marks", "marks"], ["My reports", "reports"]],
    EXAMCELL: [["Enter marks", "marks"], ["View reports", "reports"]],
  }[auth.role] || [];
  const showEvents = auth.role === "STUDENT" || auth.role === "TEACHER";

  el.innerHTML = `<div class="page-head"><div>
      <h2>Welcome, ${esc(auth.name)}</h2>
      <p class="subtle">Here's what's happening in GEU EduTrack today.</p></div></div>
    <div class="cards">${Object.entries(data.cards).map(([k, v]) => {
      const t = targets[String(k).toLowerCase()];
      return `<div class="card ${t ? "clickable" : ""}" ${t ? `data-go="${t}"` : ""}>
        <div class="num">${esc(v)}</div><div class="lbl">${esc(k)}</div></div>`;
    }).join("")}</div>
    ${showEvents ? eventsPanel() : ""}
    ${actions.length ? `<div class="panel"><h3>Quick actions</h3>
      <div class="quick">${actions.map(([label, page]) => `<button data-go="${page}">${esc(label)}</button>`).join("")}</div></div>` : ""}`;

  el.querySelectorAll("[data-go]").forEach(c => c.onclick = () => show(c.dataset.go));
};

PAGES.students = el => crudPage(el, {
  title: "Students", path: "/students/", idKey: "student_id", writeRoles: ["ADMIN"], search: true,
  pdfPath: r => "/reports/pdf/student/" + r.student_id + "/",
     deleteWarning: "This also deletes the student's enrollments, attendance and marks.",
  columns: [{ key: "roll_no", label: "Roll No" }, { key: "name", label: "Name" }, { key: "email", label: "Email" },
            { key: "branch", label: "Branch" }, { key: "year", label: "Year" }],
  fields: [{ name: "roll_no", label: "Roll No" }, { name: "name", label: "Name" },
           { name: "email", label: "Email", type: "email" }, { name: "phone", label: "Phone", required: false },
           { name: "branch", label: "Branch" }, { name: "year", label: "Year", type: "number" },
           { name: "username", label: "Login username (optional)", required: false },
           { name: "password", label: "Password (default student123)", required: false }],
});

PAGES.teachers = el => crudPage(el, {
  title: "Teachers", path: "/teachers/", idKey: "teacher_id", writeRoles: ["ADMIN"],
  columns: [{ key: "name", label: "Name" }, { key: "department", label: "Department" },
            { key: "email", label: "Email" }, { key: "phone", label: "Phone" }],
  fields: [{ name: "name", label: "Name" }, { name: "department", label: "Department" },
           { name: "email", label: "Email", type: "email" }, { name: "phone", label: "Phone", required: false },
           { name: "username", label: "Login username (optional)", required: false },
           { name: "password", label: "Password (default teacher123)", required: false }],
});

PAGES.courses = el => crudPage(el, {
  title: getAuth().role === "STUDENT" ? "My Courses" : "Courses", path: "/courses/", idKey: "course_id", writeRoles: ["ADMIN"],
  columns: [{ key: "course_name", label: "Course" }, { key: "credits", label: "Credits" }, { key: "teacher_name", label: "Teacher" }],
  fields: [{ name: "course_name", label: "Course name" }, { name: "credits", label: "Credits", type: "number" },
           { name: "teacher", label: "Teacher", from: "/teachers/", value: "teacher_id", text: t => t.name }],
});

PAGES.enrollments = el => crudPage(el, {
  title: "Enrollments", path: "/enrollments/", idKey: "enrollment_id", writeRoles: ["ADMIN"],
  columns: [{ key: "roll_no", label: "Roll No" }, { key: "student_name", label: "Student" },
            { key: "course_name", label: "Course" }, { key: "enrollment_date", label: "Date" }, { key: "status", label: "Status" }],
  fields: [{ name: "student", label: "Student", from: "/students/", value: "student_id", text: s => `${s.roll_no} - ${s.name}` },
           { name: "course", label: "Course", from: "/courses/", value: "course_id", text: c => c.course_name }],
});

PAGES.marks = el => crudPage(el, {
  title: "Marks / Results", path: "/marks/", idKey: "mark_id", writeRoles: ["ADMIN", "TEACHER", "EXAMCELL"],
  editField: "marks",
  columns: [{ key: "student_name", label: "Student" }, { key: "course_name", label: "Course" },
            { key: "exam_type", label: "Exam" }, { key: "marks", label: "Marks" }, { key: "exam_date", label: "Date" }],
  fields: [{ name: "pair", label: "Student - Course", from: "/enrollments/", value: e => e.student + "|" + e.course,
             text: e => `${e.roll_no} ${e.student_name} - ${e.course_name}` },
           { name: "exam_type", label: "Exam", options: ["Quiz", "Assignment", "Mid-Term", "End-Term"].map(x => ({ value: x, label: x })) },
           { name: "marks", label: "Marks (0-100)", type: "number" },
           { name: "exam_date", label: "Exam date", type: "date", value0: today() }],
  beforeSubmit: b => { const [student, course] = b.pair.split("|"); delete b.pair; return { ...b, student, course }; },
});

/* ---------------- attendance ---------------- */
function attendanceSummary(rows, isStudent) {
  const total = rows.length;
  const present = rows.filter(r => r.status !== "Absent").length;
  const absent = total - present;
  const pct = total ? Math.round(present * 100 / total) : 0;

  const ymd = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const now = new Date();
  const monday = new Date(now);
  monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));

  const week = ["M", "T", "W", "Th", "F"].map((name, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    const day = rows.filter(r => r.attendance_date === ymd(d));
    let cls = "none", mark = "";
    if (day.length) {
      const missed = isStudent && day.some(r => r.status === "Absent");
      cls = missed ? "absent" : "present";
      mark = missed ? "A" : "&#10003;";
    }
    return `<div class="wk"><span>${name}</span><i class="dot ${cls}">${mark}</i></div>`;
  }).join("");

  const n = now.getDate();
  const sfx = [11, 12, 13].includes(n) ? "th" : ({ 1: "st", 2: "nd", 3: "rd" }[n % 10] || "th");
  const weekday = now.toLocaleDateString("en-IN", { weekday: "long" });
  const monthYear = now.toLocaleDateString("en-IN", { month: "long", year: "numeric" });

  const ring = (value, label, fill) => {
    const r = 34, c = 2 * Math.PI * r;
    return `<div class="ring-item">
      <svg viewBox="0 0 80 80" width="92" height="92">
        <circle cx="40" cy="40" r="${r}" class="ring-bg"/>
        <circle cx="40" cy="40" r="${r}" class="ring-fg" stroke-dasharray="${c * fill} ${c}" transform="rotate(-90 40 40)"/>
        <text x="40" y="46" text-anchor="middle" class="ring-num">${value}</text>
      </svg><div class="ring-label">${label}</div></div>`;
  };

  return `<div class="att-top">
    <div class="att-card">
      <div class="att-date"><div class="att-day">${n}<sup>${sfx}</sup></div>
        <div><div class="att-wd">${weekday}</div><div class="att-my">${monthYear}</div></div></div>
      <p class="att-sub">${isStudent ? "This week status" : "Attendance taken this week"}</p>
      <div class="week">${week}</div>
    </div>
    <div class="att-card rings">
      ${ring(pct + "%", isStudent ? "Attendance" : "Class attendance", pct / 100)}
      ${ring(absent, "Absences", total ? absent / total : 0)}
      ${ring(total, isStudent ? "Classes held" : "Records marked", total ? 1 : 0)}
    </div></div>`;
}

PAGES.attendance = async el => {
  const role = getAuth().role;
  const canMark = role === "ADMIN" || role === "TEACHER";
  const courses = role === "STUDENT" ? [] : await api("/courses/");
  const courseOpts = courses.map(c => `<option value="${c.course_id}">${esc(c.course_name)}</option>`).join("");

  el.innerHTML = `<h2>Attendance</h2><div id="summary"></div>
    ${canMark ? `<div class="panel"><h3>Mark attendance</h3>
      <div class="grid"><div><label>Course</label><select id="mCourse">${courseOpts}</select></div>
      <div><label>Date</label><input id="mDate" type="date" value="${today()}"></div>
      <div><button id="loadStu">Load students</button></div></div>
      <div id="roster"></div><div id="markMsg"></div></div>` : ""}
    <div class="panel"><h3>Records</h3>
      ${role !== "STUDENT" ? `<div class="grid"><div><label>Course</label><select id="fCourse"><option value="">All</option>${courseOpts}</select></div>
        <div><label>Date</label><input id="fDate" type="date"></div><div><button id="filterBtn">Filter</button></div></div>` : ""}
      <div id="records"></div></div>`;

  async function loadSummary() {
    const all = await api("/attendance/");
    el.querySelector("#summary").innerHTML = attendanceSummary(all, role === "STUDENT");
  }

  async function loadRecords() {
    const params = new URLSearchParams();
    if (el.querySelector("#fCourse")?.value) params.set("course", el.querySelector("#fCourse").value);
    if (el.querySelector("#fDate")?.value) params.set("date", el.querySelector("#fDate").value);
    const rows = await api("/attendance/?" + params);
    el.querySelector("#records").innerHTML = buildTable([
      { key: "attendance_date", label: "Date" }, { key: "student_name", label: "Student" },
      { key: "course_name", label: "Course" },
      { label: "Status", fmt: r => r.status === "Absent" ? '<span class="low">Absent</span>' : "Present" }], rows);
  }

  if (canMark) {
    el.querySelector("#loadStu").onclick = async () => {
      const course = el.querySelector("#mCourse").value;
      const roster = el.querySelector("#roster");
      const list = (await api("/enrollments/")).filter(e => String(e.course) === course);
      if (!list.length) { roster.innerHTML = '<div class="empty">No students enrolled in this course.</div>'; return; }
      roster.innerHTML = `<table><thead><tr><th>Roll No</th><th>Student</th><th>Present</th><th>Absent</th></tr></thead><tbody>${
        list.map(e => `<tr><td>${esc(e.roll_no)}</td><td>${esc(e.student_name)}</td>
          <td><input type="radio" name="s${e.student}" value="Present" checked></td>
          <td><input type="radio" name="s${e.student}" value="Absent"></td></tr>`).join("")
      }</tbody></table><button id="saveAtt" style="margin-top:10px">Save attendance</button>`;
      el.querySelector("#saveAtt").onclick = async () => {
        const records = list.map(e => ({ student: e.student, status: roster.querySelector(`input[name=s${e.student}]:checked`).value }));
        try {
          const r = await api("/attendance/bulk/", "POST", { course, date: el.querySelector("#mDate").value, records });
          notify(el.querySelector("#markMsg"), `Saved ${r.saved} records.`, true);
          loadRecords();
          loadSummary();
        } catch (e) { notify(el.querySelector("#markMsg"), e.message); }
      };
    };
  }
  if (role !== "STUDENT") el.querySelector("#filterBtn").onclick = () => loadRecords().catch(e => alert(e.message));
  await loadSummary();
  await loadRecords();
};

/* ---------------- reports ---------------- */
PAGES.reports = async el => {
  const role = getAuth().role;
  el.innerHTML = `<h2>Reports</h2>
    <div class="toolbar" id="pdfBar">
      ${role !== "EXAMCELL" ? '<button data-pdf="attendance">Download attendance report (PDF)</button>' : ""}
      <button data-pdf="performance">Download performance report (PDF)</button>
      ${role === "STUDENT" ? '<button data-pdf="mine">Download my full report (PDF)</button>' : ""}
        </div><div id="pdfMsg"></div><div id="myReq"></div><div id="repBody"></div>`;
  const bar = el.querySelector("#pdfBar");
    async function loadRequests() {
    if (role === "ADMIN") return;  // Admin downloads instantly, so there is no list
    const box = el.querySelector("#myReq");
    const rows = await api("/reports/requests/");
    box.innerHTML = `<div class="panel"><h3>My requests</h3>${buildTable([
      { key: "task_name", label: "Report" },
      { label: "Status", fmt: r => r.can_download ? "Approved" : "Waiting for approval" }],
      rows, r => r.can_download ? `<button data-dl="${r.process_id}">Download</button>` : "")}</div>`;
    box.querySelectorAll("[data-dl]").forEach(b => b.onclick = async () => {
      try { await downloadApproved(b.dataset.dl); }
      catch (e) { notify(el.querySelector("#pdfMsg"), e.message); }
    });
  }
  loadRequests().catch(e => notify(el.querySelector("#pdfMsg"), e.message));
  bar.querySelectorAll("button").forEach(b => b.onclick = async () => {
    const note = el.querySelector("#pdfMsg"); notify(note, "");
    b.disabled = true;
    try {
            let kind = b.dataset.pdf, studentId = null;
      if (kind === "mine") { kind = "student"; studentId = (await api("/students/"))[0].student_id; }
      const res = await requestReport(kind, studentId);
            loadRequests();
      notify(note, res.instant ? "PDF downloaded." : "Request sent. It is waiting for the Admin's approval.", true);
    } catch (e) { notify(note, e.message); }
    b.disabled = false;
  });
  const body = el.querySelector("#repBody");
  body.innerHTML = "";
  if (role !== "EXAMCELL") {
    const att = await api("/reports/attendance/");
    body.innerHTML += `<div class="panel"><h3>Attendance report (below 75% is highlighted)</h3>${buildTable([
      { key: "roll_no", label: "Roll No" }, { key: "student_name", label: "Student" }, { key: "course_name", label: "Course" },
      { key: "total_classes", label: "Classes" }, { key: "present", label: "Present" },
      { label: "Attendance %", fmt: r => r.percentage === null ? "-" : `<span class="${r.low ? "low" : ""}">${r.percentage}%</span>` }], att)}</div>`;
  }
  const perf = await api("/reports/performance/");
  body.innerHTML += `<div class="panel"><h3>Academic performance (average marks)</h3>${buildTable([
    { key: "roll_no", label: "Roll No" }, { key: "student_name", label: "Student" }, { key: "course_name", label: "Course" },
    { key: "exams", label: "Exams" }, { label: "Average", fmt: r => r.average === null ? "-" : r.average }], perf)}</div>`;
};

/* ---------------- OS scheduler (Phase 2: simulation on entered data) ---------------- */
PAGES.scheduler = async el => {
  const sample = [["P1", 0, 6, 2], ["P2", 1, 8, 1], ["P3", 2, 3, 3], ["P4", 3, 4, 2]];
  el.innerHTML = `<h2>OS Scheduler</h2>
    <div class="panel"><h3>Processes (system tasks such as report generation)</h3>
      <table id="pt"><thead><tr><th>PID</th><th>Arrival</th><th>Burst</th><th>Priority (1 = highest)</th><th></th></tr></thead><tbody></tbody></table>
      <div class="toolbar" style="margin-top:12px">
        <button class="secondary" id="addRow">+ Add process</button>
        <select id="algo" style="max-width:220px"><option value="FCFS">FCFS</option><option value="SJF">SJF (non-preemptive)</option><option value="PRIORITY">Priority (non-preemptive)</option></select>
        <button id="run">Run scheduler</button></div>
      <div id="schMsg"></div></div>
    <div id="out"></div>`;
  const tbody = el.querySelector("#pt tbody");
  const addRow = (v = ["", 0, 1, 1]) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><input value="${v[0] || "P" + (tbody.children.length + 1)}"></td><td><input type="number" min="0" value="${v[1]}"></td>
      <td><input type="number" min="1" value="${v[2]}"></td><td><input type="number" min="1" value="${v[3]}"></td>
      <td><button class="danger">x</button></td>`;
    tr.querySelector("button").onclick = () => tr.remove();
    tbody.appendChild(tr);
  };
  sample.forEach(addRow);
  el.querySelector("#addRow").onclick = () => addRow();

  el.querySelector("#run").onclick = async () => {
    const msg = el.querySelector("#schMsg"); notify(msg, "");
    const processes = [...tbody.children].map(tr => {
      const i = tr.querySelectorAll("input");
      return { pid: i[0].value, arrival: i[1].value, burst: i[2].value, priority: i[3].value };
    });
    const chosen = el.querySelector("#algo").value;
    try {
      const all = await Promise.all(["FCFS", "SJF", "PRIORITY"].map(a => api("/scheduler/simulate/", "POST", { algorithm: a, processes })));
      const r = all.find(x => x.algorithm === chosen);
      el.querySelector("#out").innerHTML = `
        <div class="panel"><h3>${r.algorithm} - results</h3>${buildTable([
          { key: "pid", label: "PID" }, { key: "arrival", label: "AT" }, { key: "burst", label: "BT" }, { key: "priority", label: "Prio" },
          { key: "completion", label: "CT" }, { key: "turnaround", label: "TAT" }, { key: "waiting", label: "WT" }], r.results)}
          <p style="margin-top:8px"><b>Average WT:</b> ${r.avg_waiting} &nbsp; <b>Average TAT:</b> ${r.avg_turnaround}</p></div>
        <div class="panel"><h3>Gantt chart</h3><div class="gantt">${r.gantt.map((g, i) =>
          `<div class="gbox ${g.pid === "IDLE" ? "idle" : ""}" style="width:${Math.max(34, (g.end - g.start) * 30)}px">${esc(g.pid)}
            <span class="s">${g.start}</span>${i === r.gantt.length - 1 ? `<span class="e">${g.end}</span>` : ""}</div>`).join("")}</div></div>
        <div class="panel"><h3>Process state log (READY - RUNNING - COMPLETED)</h3><div class="states">${r.timeline.map(t =>
          `<span>t=${t.time}: ${esc(t.pid)} &rarr; ${t.state}</span>`).join("")}</div></div>
        <div class="panel"><h3>Algorithm comparison</h3>${buildTable([
          { key: "algorithm", label: "Algorithm" }, { key: "avg_waiting", label: "Avg WT" }, { key: "avg_turnaround", label: "Avg TAT" }], all)}</div>`;
    } catch (e) { notify(msg, e.message); }
  };
};

/* ---------------- OS scheduler (reads the process queue from the os_process table) ---------------- */
PAGES.scheduler = async el => {
  const types = ["ATTENDANCE_REPORT", "MARKS_REPORT", "STUDENT_REPORT", "COURSE_SUMMARY", "NOTIFICATION"];
  el.innerHTML = `<h2>OS Scheduler</h2>
        <div class="panel"><h3>Waiting for approval</h3>
      <div id="queue"></div>
      <div class="toolbar" style="margin-top:12px">
        <select id="algo" style="max-width:240px">
          <option value="FCFS">FCFS</option>
          <option value="SJF">SJF (non-preemptive)</option>
          <option value="PRIORITY">Priority (non-preemptive)</option>
        </select>
        <button id="run">Run scheduler</button>
        <button class="secondary" id="reset">Reset queue</button>
      </div>
      <div id="schMsg"></div></div>
        <div id="doneQueue"></div>
      <div class="panel"><h3>Add a process</h3>
      <form id="pForm" class="grid">
        <div><label>Task name</label><input name="task_name" required></div>
        <div><label>Type</label><select name="task_type">${types.map(t => `<option>${t}</option>`).join("")}</select></div>
        <div><label>Arrival time</label><input name="arrival_time" type="number" min="0" value="0" required></div>
        <div><label>Burst time</label><input name="burst_time" type="number" min="1" value="3" required></div>
        <div><label>Priority (1 = highest)</label><input name="priority" type="number" min="1" value="2" required></div>
        <div><button type="submit">Add</button></div>
      </form></div>
    <div id="out"></div>`;
  const msg = el.querySelector("#schMsg");

    async function loadQueue() {
    const rows = await api("/processes/");
    const waiting = rows.filter(r => r.state !== "COMPLETED");
    const done = rows.filter(r => r.state === "COMPLETED")
      .sort((a, b) => (a.approved_at || "").localeCompare(b.approved_at || ""));

    // Table 1: requests that still need approval
    el.querySelector("#queue").innerHTML = buildTable([
      { label: "PID", fmt: r => "P" + r.process_id }, { key: "task_name", label: "Task" }, { key: "task_type", label: "Type" },
      { key: "requested_by_name", label: "Requested by" },
      { key: "arrival_time", label: "AT" }, { key: "burst_time", label: "BT" }, { key: "priority", label: "Priority" },
      { key: "state", label: "State" }],
      waiting, r => `<button class="danger" data-del="${r.process_id}">Delete</button>`);

    // Table 2: approved requests, in the order they were approved
    el.querySelector("#doneQueue").innerHTML = `<div class="panel"><h3>Completed requests (in the order they were approved)</h3>${buildTable([
      { label: "#", fmt: r => done.indexOf(r) + 1 },
      { label: "PID", fmt: r => "P" + r.process_id }, { key: "task_name", label: "Task" },
      { key: "requested_by_name", label: "Requested by" }, { key: "priority", label: "Priority" },
      { key: "completion_time", label: "CT" }, { key: "turnaround_time", label: "TAT" }, { key: "waiting_time", label: "WT" },
      { label: "Approved at", fmt: r => r.approved_at ? esc(new Date(r.approved_at).toLocaleString("en-IN")) : "-" }],
      done)}</div>`;

    el.querySelectorAll("[data-del]").forEach(b => b.onclick = async () => {
      try { await api("/processes/" + b.dataset.del + "/", "DELETE"); loadQueue(); }
      catch (e) { notify(msg, e.message); }
    });
  }

  el.querySelector("#pForm").onsubmit = async ev => {
    ev.preventDefault();
    const body = {};
    new FormData(ev.target).forEach((v, k) => { body[k] = v; });
    try { await api("/processes/", "POST", body); ev.target.reset(); notify(msg, "Process added.", true); loadQueue(); }
    catch (e) { notify(msg, e.message); }
  };

  el.querySelector("#reset").onclick = async () => {
    try {
      await api("/scheduler/reset/", "POST");
      el.querySelector("#out").innerHTML = "";
      notify(msg, "Queue reset. All processes are READY again.", true);
      loadQueue();
    } catch (e) { notify(msg, e.message); }
  };

  el.querySelector("#run").onclick = async () => {
    notify(msg, "");
    try {
      const r = await api("/scheduler/run/", "POST", { algorithm: el.querySelector("#algo").value });
      el.querySelector("#out").innerHTML = `
        <div class="panel"><h3>${r.algorithm} - results (saved to os_process)</h3>${buildTable([
          { key: "pid", label: "PID" }, { key: "task_name", label: "Task" }, { key: "arrival", label: "AT" },
          { key: "burst", label: "BT" }, { key: "priority", label: "Prio" }, { key: "completion", label: "CT" },
          { key: "turnaround", label: "TAT" }, { key: "waiting", label: "WT" }], r.results)}
          <p style="margin-top:8px"><b>Average WT:</b> ${r.avg_waiting} &nbsp; <b>Average TAT:</b> ${r.avg_turnaround}</p></div>
        <div class="panel"><h3>Gantt chart</h3><div class="gantt">${r.gantt.map((g, i) =>
          `<div class="gbox ${g.pid === "IDLE" ? "idle" : ""}" style="width:${Math.max(34, (g.end - g.start) * 30)}px">${esc(g.pid)}
            <span class="s">${g.start}</span>${i === r.gantt.length - 1 ? `<span class="e">${g.end}</span>` : ""}</div>`).join("")}</div></div>
        <div class="panel"><h3>Process state log (READY - RUNNING - COMPLETED)</h3><div class="states">${r.timeline.map(t =>
          `<span>t=${t.time}: ${esc(t.pid)} &rarr; ${t.state}</span>`).join("")}</div></div>
        <div class="panel"><h3>Algorithm comparison</h3>${buildTable([
          { key: "algorithm", label: "Algorithm" }, { key: "avg_waiting", label: "Avg WT" }, { key: "avg_turnaround", label: "Avg TAT" }], r.comparison)}</div>`;
      loadQueue();
    } catch (e) { notify(msg, e.message); }
  };

  await loadQueue();
};