"""
Deadlock handling for EduTrack system tasks (report generation etc.)

Resources are things a task must hold while it runs, e.g. PDF Engine, DB Connection, Table Lock.
Matrices: rows = processes, columns = resource types.

  detect()          DETECTION  - is the system already deadlocked? (needs Allocation, Request, Available)
  bankers_safety()  AVOIDANCE  - is the current state safe?        (needs Max, Allocation, Available)
  bankers_request() AVOIDANCE  - may this request be granted safely?
"""


def _names(n):
    return [f"P{i}" for i in range(n)]


def _check_shapes(available, **matrices):
    m = len(available)
    for name, mat in matrices.items():
        if not mat or any(len(row) != m for row in mat):
            raise ValueError(f"{name} must have one row per process and {m} columns.")
    n = len(next(iter(matrices.values())))
    if any(len(mat) != n for mat in matrices.values()):
        raise ValueError("All matrices must have the same number of processes.")
    return n, m


def detect(allocation, request, available):
    """Deadlock DETECTION. A process that can finish with the free resources releases what it holds;
    whoever is still stuck at the end is deadlocked."""
    n, m = _check_shapes(available, allocation=allocation, request=request)
    work = list(available)
    finish = [all(x == 0 for x in allocation[i]) for i in range(n)]  # holding nothing = cannot be in a deadlock
    names, order, steps = _names(n), [], []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and all(request[i][j] <= work[j] for j in range(m)):
                work = [work[j] + allocation[i][j] for j in range(m)]
                finish[i] = True
                order.append(names[i])
                steps.append({"process": names[i], "work_after": list(work)})
                progress = True
    stuck = [names[i] for i in range(n) if not finish[i]]
    return {"deadlocked": bool(stuck), "deadlocked_processes": stuck,
            "finish_order": order, "steps": steps, "work_final": work}


def bankers_safety(available, maximum, allocation):
    """Banker's algorithm safety check (AVOIDANCE): is there an order in which every process can finish?"""
    n, m = _check_shapes(available, maximum=maximum, allocation=allocation)
    need = [[maximum[i][j] - allocation[i][j] for j in range(m)] for i in range(n)]
    if any(x < 0 for row in need for x in row):
        raise ValueError("Allocation cannot be larger than Max for any process.")
    work = list(available)
    finish = [False] * n
    names, sequence, steps = _names(n), [], []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                work = [work[j] + allocation[i][j] for j in range(m)]
                finish[i] = True
                sequence.append(names[i])
                steps.append({"process": names[i], "work_after": list(work)})
                progress = True
    safe = all(finish)
    return {"safe": safe, "safe_sequence": sequence if safe else [], "need": need, "steps": steps,
            "unfinished": [names[i] for i in range(n) if not finish[i]]}


def bankers_request(available, maximum, allocation, process, request):
    """Resource-request algorithm: pretend to grant the request, then run the safety check."""
    n, m = _check_shapes(available, maximum=maximum, allocation=allocation)
    if not 0 <= process < n or len(request) != m:
        raise ValueError("Pick a valid process and give one number per resource.")
    need = [maximum[process][j] - allocation[process][j] for j in range(m)]
    name = f"P{process}"
    if any(request[j] > need[j] for j in range(m)):
        return {"granted": False, "reason": f"{name} asked for more than its declared maximum need."}
    if any(request[j] > available[j] for j in range(m)):
        return {"granted": False, "reason": f"Not enough free resources, so {name} must wait."}
    new_avail = [available[j] - request[j] for j in range(m)]
    new_alloc = [list(r) for r in allocation]
    new_alloc[process] = [allocation[process][j] + request[j] for j in range(m)]
    check = bankers_safety(new_avail, maximum, new_alloc)
    if check["safe"]:
        return {"granted": True, "reason": "Granting it keeps the system in a safe state.",
                "safe_sequence": check["safe_sequence"]}
    return {"granted": False, "reason": "Granting it would leave the system in an UNSAFE state, so it is refused."}