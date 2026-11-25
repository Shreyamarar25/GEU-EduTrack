// Deadlock + Synchronization pages (Shreya). Loaded after pages.js. Admin only.

/* ===================== DEADLOCK: detection (Banker's) + avoidance ===================== */
PAGES.deadlock = async el => {
  const RES = ["PDF Engine", "DB Connection", "Table Lock"];
  const PROC = ["P0 Attendance report", "P1 Performance report", "P2 Student report", "P3 Notifications", "P4 Course summary"];
  const zeros = () => PROC.map(() => RES.map(() => 0));
  const EXAMPLES = {
    safe: { alloc: [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
            max: [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]], req: zeros(), avail: [3, 3, 2] },
    dead: { alloc: [[0, 1, 0], [2, 0, 0], [3, 0, 3], [2, 1, 1], [0, 0, 2]],
            req: [[0, 0, 0], [2, 0, 2], [0, 0, 1], [1, 0, 0], [0, 0, 2]], avail: [0, 0, 0] },
  };
  EXAMPLES.dead.max = EXAMPLES.dead.alloc.map((row, i) => row.map((v, j) => v + EXAMPLES.dead.req[i][j]));

  const cell = (m, i, j) => `<td><input type="number" min="0" data-m="${m}" data-i="${i}" data-j="${j}" value="0" style="width:62px"></td>`;
  el.innerHTML = `<h2>Deadlock: detection and avoidance</h2>
    <div class="panel"><h3>Resources and processes</h3>
      <p style="color:#666;font-size:13px;margin-bottom:10px">Each report task holds resources (PDF Engine, DB Connection, Table Lock) while it runs.
        <b>Allocation</b> = what it holds now, <b>Max</b> = most it will ever need, <b>Request</b> = what it is waiting for now.</p>
      <div class="toolbar"><button class="secondary" id="exSafe">Load safe example</button>
        <button class="secondary" id="exDead">Load deadlock example</button></div>
      <table><thead>
        <tr><th rowspan="2">Process (task)</th><th colspan="3">Allocation</th><th colspan="3">Max</th><th colspan="3">Request</th></tr>
        <tr>${["alloc", "max", "req"].map(() => RES.map(r => `<th>${r}</th>`).join("")).join("")}</tr></thead>
        <tbody>${PROC.map((p, i) => `<tr><td>${p}</td>${["alloc", "max", "req"].map(m => RES.map((_, j) => cell(m, i, j)).join("")).join("")}</tr>`).join("")}</tbody></table>
      <h3 style="margin-top:14px">Available (free instances now)</h3>
      <table style="max-width:520px"><thead><tr>${RES.map(r => `<th>${r}</th>`).join("")}</tr></thead>
        <tbody><tr>${RES.map((_, j) => cell("avail", 0, j)).join("")}</tr></tbody></table>
      <div class="toolbar" style="margin-top:12px">
        <button id="bSafe">Check safe state (Banker's - avoidance)</button>
        <button id="bDetect">Detect deadlock</button></div></div>
    <div class="panel"><h3>Ask for resources (Banker's request algorithm)</h3>
      <div class="grid">
        <div><label>Process</label><select id="rProc">${PROC.map((p, i) => `<option value="${i}">${p}</option>`).join("")}</select></div>
        ${RES.map((r, j) => `<div><label>${r}</label><input type="number" min="0" value="0" id="rv${j}"></div>`).join("")}
        <div><button id="bReq">Request</button></div></div></div>
    <div id="out"></div>`;
  const out = el.querySelector("#out");
  const input = (m, i, j) => el.querySelector(`input[data-m="${m}"][data-i="${i}"][data-j="${j}"]`);
  const load = ex => {
    PROC.forEach((_, i) => RES.forEach((_, j) => ["alloc", "max", "req"].forEach(m => { input(m, i, j).value = ex[m][i][j]; })));
    RES.forEach((_, j) => { input("avail", 0, j).value = ex.avail[j]; });
    out.innerHTML = "";
  };
  const matrix = m => PROC.map((_, i) => RES.map((_, j) => Number(input(m, i, j).value || 0)));
  const avail = () => RES.map((_, j) => Number(input("avail", 0, j).value || 0));
  const box = (ok, html) => `<div class="msg ${ok ? "ok" : "err"}" style="font-size:15px">${html}</div>`;
  const stepTable = list => buildTable([{ key: "process", label: "Process finishes" },
    { label: "Free resources after it releases its hold  (" + RES.join(", ") + ")", fmt: r => esc(r.work_after.join(", ")) }], list);

  el.querySelector("#exSafe").onclick = () => load(EXAMPLES.safe);
  el.querySelector("#exDead").onclick = () => load(EXAMPLES.dead);
  load(EXAMPLES.safe);

  el.querySelector("#bSafe").onclick = async () => {
    try {
      const r = await api("/os/deadlock/safety/", "POST", { available: avail(), maximum: matrix("max"), allocation: matrix("alloc") });
      out.innerHTML = `<div class="panel"><h3>Banker's safety check</h3>` + (r.safe
        ? box(true, "<b>SAFE state.</b> Safe sequence: " + r.safe_sequence.join(" &rarr; "))
        : box(false, "<b>UNSAFE state.</b> These processes cannot be guaranteed to finish: " + r.unfinished.join(", "))) +
        `<h3 style="margin-top:12px">Need = Max - Allocation</h3>` +
        buildTable([{ key: "p", label: "Process" }, ...RES.map((n, j) => ({ label: n, fmt: r2 => r2.n[j] }))],
          r.need.map((n, i) => ({ p: PROC[i], n }))) +
        (r.steps.length ? `<h3 style="margin-top:12px">How the sequence was found</h3>` + stepTable(r.steps) : "") + "</div>";
    } catch (e) { out.innerHTML = box(false, esc(e.message)); }
  };

  el.querySelector("#bDetect").onclick = async () => {
    try {
      const r = await api("/os/deadlock/detect/", "POST", { available: avail(), allocation: matrix("alloc"), request: matrix("req") });
      out.innerHTML = `<div class="panel"><h3>Deadlock detection</h3>` + (r.deadlocked
        ? box(false, "<b>DEADLOCK DETECTED.</b> Deadlocked processes: " + r.deadlocked_processes.join(", "))
        : box(true, "<b>No deadlock.</b> Every process can finish, in this order: " + r.finish_order.join(" &rarr; "))) +
        (r.steps.length ? `<h3 style="margin-top:12px">Processes that could finish</h3>` + stepTable(r.steps) : "") + "</div>";
    } catch (e) { out.innerHTML = box(false, esc(e.message)); }
  };

  el.querySelector("#bReq").onclick = async () => {
    try {
      const r = await api("/os/deadlock/request/", "POST", { available: avail(), maximum: matrix("max"), allocation: matrix("alloc"),
        process: Number(el.querySelector("#rProc").value), request: RES.map((_, j) => Number(el.querySelector("#rv" + j).value || 0)) });
      out.innerHTML = `<div class="panel"><h3>Resource request</h3>` + box(r.granted,
        (r.granted ? "<b>GRANTED.</b> " : "<b>REFUSED.</b> ") + esc(r.reason) +
        (r.safe_sequence ? "<br>Safe sequence afterwards: " + r.safe_sequence.join(" &rarr; ") : "")) + "</div>";
    } catch (e) { out.innerHTML = box(false, esc(e.message)); }
  };
};

/* ===================== SYNCHRONIZATION: mutex, semaphores, producer-consumer ===================== */
PAGES.sync = async el => {
  el.innerHTML = `<h2>Process synchronization</h2>
    <div class="panel"><h3>1. Race condition and mutex</h3>
      <p style="color:#666;font-size:13px;margin-bottom:10px">Several threads add 1 to the same shared counter. Each one reads the value, pauses a moment, then writes back value + 1.
        Without a <b>mutex</b> they overwrite each other's updates, so the final number is too small.</p>
      <div class="grid">
        <div><label>Threads</label><input type="number" id="rcW" min="2" max="8" value="4"></div>
        <div><label>Additions per thread</label><input type="number" id="rcI" min="10" max="500" value="100"></div>
        <div><button class="danger" id="rcNo" style="padding:8px 16px;font-size:14px">Run WITHOUT mutex</button></div>
        <div><button id="rcYes">Run WITH mutex</button></div></div>
      <div id="rcMsg"></div><div id="rcOut"></div></div>
    <div class="panel"><h3>2. Producer - consumer (the report-request queue)</h3>
      <p style="color:#666;font-size:13px;margin-bottom:10px"><b>Producers</b> = users sending report requests, <b>consumer</b> = the scheduler approving them.
        The queue has a limited size. Two <b>semaphores</b> (<i>empty</i> = free slots, <i>full</i> = waiting requests) make producers wait when the queue is full
        and the scheduler wait when it is empty. A <b>mutex</b> lets only one thread change the queue at a time.</p>
      <div class="grid">
        <div><label>Queue size (slots)</label><input type="number" id="pcC" min="1" max="6" value="3"></div>
        <div><label>Producers</label><input type="number" id="pcP" min="1" max="5" value="3"></div>
        <div><label>Schedulers (consumers)</label><input type="number" id="pcS" min="1" max="3" value="1"></div>
        <div><label>Requests per producer</label><input type="number" id="pcI" min="1" max="6" value="3"></div>
        <div><button id="pcRun">Run</button></div></div>
      <div id="pcMsg"></div><div id="pcOut"></div></div>`;
  const rows = [];

  async function race(useMutex, btn) {
    const msg = el.querySelector("#rcMsg"); notify(msg, "");
    btn.disabled = true;
    try {
      const r = await api("/os/sync/race/", "POST", { workers: el.querySelector("#rcW").value,
        increments: el.querySelector("#rcI").value, use_mutex: useMutex });
      rows.unshift(r);
      el.querySelector("#rcOut").innerHTML = buildTable([
        { label: "Mode", fmt: x => x.use_mutex ? "WITH mutex" : "WITHOUT mutex" }, { key: "workers", label: "Threads" },
        { key: "expected", label: "Expected total" }, { key: "actual", label: "Actual total" }, { key: "lost_updates", label: "Lost updates" },
        { label: "Result", fmt: x => x.correct ? '<b style="color:#2e8b57">Correct</b>' : '<b class="low">Wrong (race condition)</b>' }], rows);
    } catch (e) { notify(msg, e.message); }
    btn.disabled = false;
  }
  el.querySelector("#rcNo").onclick = ev => race(false, ev.target);
  el.querySelector("#rcYes").onclick = ev => race(true, ev.target);

  el.querySelector("#pcRun").onclick = async ev => {
    const btn = ev.target, msg = el.querySelector("#pcMsg"); notify(msg, "");
    btn.disabled = true; btn.textContent = "Running...";
    try {
      const r = await api("/os/sync/producer-consumer/", "POST", { capacity: el.querySelector("#pcC").value,
        producers: el.querySelector("#pcP").value, consumers: el.querySelector("#pcS").value, items: el.querySelector("#pcI").value });
      el.querySelector("#pcOut").innerHTML = `
        <div class="msg ${r.completed && r.never_overflowed ? "ok" : "err"}" style="font-size:15px">
          Produced <b>${r.produced}</b>, approved <b>${r.consumed}</b>. The queue never held more than <b>${r.max_buffer_size}</b> of ${r.capacity} slots
          (${r.never_overflowed ? "no overflow" : "OVERFLOW"}). ${r.completed ? "All requests were handled, no deadlock." : "Did not finish."}</div>` +
        buildTable([{ key: "step", label: "Step" }, { key: "actor", label: "Who" }, { key: "action", label: "Action" }, { key: "item", label: "Request" },
          { label: "Queue after this step", fmt: x => x.buffer.length ? esc(x.buffer.join(", ")) : "(empty)" },
          { label: "Size", fmt: x => x.size + " / " + r.capacity }], r.log);
    } catch (e) { notify(msg, e.message); }
    btn.disabled = false; btn.textContent = "Run";
  };
};