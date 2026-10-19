"""
EduTrack OS Scheduler (Phase 2 - standalone, non-preemptive)
Algorithms: FCFS, SJF, PRIORITY   (lower priority number = higher priority)
Outputs per process: CT (completion), TAT (turnaround = CT - AT), WT (waiting = TAT - BT)
Also returns a Gantt chart and a state timeline (READY -> RUNNING -> COMPLETED).

Run it directly to test:  python scheduler/scheduler.py
"""

ALGORITHMS = ("FCFS", "SJF", "PRIORITY")


def _clean(processes):
    cleaned = []
    for i, p in enumerate(processes):
        try:
            item = {
                "pid": str(p.get("pid") or f"P{i + 1}"),
                "arrival": int(p.get("arrival", 0)),
                "burst": int(p["burst"]),
                "priority": int(p.get("priority", 1)),
                "_order": i,
            }
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Process {i + 1}: arrival, burst and priority must be whole numbers.")
        if item["burst"] <= 0 or item["arrival"] < 0:
            raise ValueError(f"Process {item['pid']}: burst must be > 0 and arrival >= 0.")
        cleaned.append(item)
    if not cleaned:
        raise ValueError("Add at least one process.")
    return cleaned


def _pick_key(algorithm):
    if algorithm == "FCFS":
        return lambda p: (p["arrival"], p["_order"])
    if algorithm == "SJF":
        return lambda p: (p["burst"], p["arrival"], p["_order"])
    return lambda p: (p["priority"], p["arrival"], p["_order"])  # PRIORITY


def schedule(processes, algorithm="FCFS"):
    algorithm = algorithm.upper()
    if algorithm not in ALGORITHMS:
        raise ValueError(f"Algorithm must be one of {ALGORITHMS}")

    procs = _clean(processes)
    key = _pick_key(algorithm)
    pending, done = list(procs), {}
    time, gantt, timeline = 0, [], []

    for p in procs:
        timeline.append({"time": p["arrival"], "pid": p["pid"], "state": "READY"})

    while pending:
        ready = [p for p in pending if p["arrival"] <= time]
        if not ready:  # CPU idle until next process arrives
            next_arrival = min(p["arrival"] for p in pending)
            gantt.append({"pid": "IDLE", "start": time, "end": next_arrival})
            time = next_arrival
            continue
        chosen = min(ready, key=key)
        start, end = time, time + chosen["burst"]
        gantt.append({"pid": chosen["pid"], "start": start, "end": end})
        timeline.append({"time": start, "pid": chosen["pid"], "state": "RUNNING"})
        timeline.append({"time": end, "pid": chosen["pid"], "state": "COMPLETED"})
        tat = end - chosen["arrival"]
        done[chosen["_order"]] = {
            "pid": chosen["pid"], "arrival": chosen["arrival"], "burst": chosen["burst"],
            "priority": chosen["priority"], "completion": end,
            "turnaround": tat, "waiting": tat - chosen["burst"],
        }
        pending.remove(chosen)
        time = end

    results = [done[i] for i in sorted(done)]
    n = len(results)
    timeline.sort(key=lambda e: (e["time"], ["READY", "RUNNING", "COMPLETED"].index(e["state"])))
    return {
        "algorithm": algorithm,
        "results": results,
        "gantt": gantt,
        "timeline": timeline,
        "avg_waiting": round(sum(r["waiting"] for r in results) / n, 2),
        "avg_turnaround": round(sum(r["turnaround"] for r in results) / n, 2),
    }


if __name__ == "__main__":
    sample = [
        {"pid": "P1", "arrival": 0, "burst": 6, "priority": 2},
        {"pid": "P2", "arrival": 1, "burst": 8, "priority": 1},
        {"pid": "P3", "arrival": 2, "burst": 3, "priority": 3},
        {"pid": "P4", "arrival": 3, "burst": 4, "priority": 2},
    ]
    for algo in ALGORITHMS:
        out = schedule(sample, algo)
        print(f"\n=== {algo} ===")
        for r in out["results"]:
            print(r)
        print("Gantt:", " | ".join(f"{g['pid']}({g['start']}-{g['end']})" for g in out["gantt"]))
        print("Avg WT:", out["avg_waiting"], " Avg TAT:", out["avg_turnaround"])
