"""Builds the live resource picture from the real tasks in os_process (used by the deadlock logic)."""
from .resources import RESOURCE_NAMES, POOL, need_for


def parse_held(text):
    """Turns the stored text '1,0,1' into the list [1, 0, 1]. Anything unreadable counts as holding nothing."""
    try:
        numbers = [int(x) for x in str(text).split(",")]
    except ValueError:
        numbers = []
    return numbers if len(numbers) == len(POOL) else [0] * len(POOL)


def live_state():
    """What every RUNNING task holds, the most it may need, and what is still free."""
    from academics.models import OsProcess
    tasks = list(OsProcess.objects.filter(state="RUNNING").order_by("process_id"))
    allocation = [parse_held(t.held) for t in tasks]
    maximum = [need_for(t.report_kind) for t in tasks]
    available = [POOL[j] - sum(row[j] for row in allocation) for j in range(len(POOL))]
    return {
        "resources": RESOURCE_NAMES,
        "pool": POOL,
        "ids": [t.process_id for t in tasks],
        "names": [t.task_name for t in tasks],
        "allocation": allocation,
        "maximum": maximum,
        "available": available,
    }


def to_text(numbers):
    """Turns the list [1, 0, 1] into the text '1,0,1' that is stored in the held column."""
    return ",".join(str(n) for n in numbers)


def is_safe(available, maximum, allocation):
    """Banker's safety check. True if the tasks can all finish in some order.
    Also returns that order as positions in the lists (0 = first task)."""
    work = list(available)
    done = [False] * len(allocation)
    order = []
    progress = True
    while progress:
        progress = False
        for i in range(len(allocation)):
            still_needs = [maximum[i][j] - allocation[i][j] for j in range(len(work))]
            if not done[i] and all(still_needs[j] <= work[j] for j in range(len(work))):
                work = [work[j] + allocation[i][j] for j in range(len(work))]   # it finishes and gives everything back
                done[i] = True
                order.append(i)
                progress = True
    return all(done), order


def check_start(task, protect=True):
    """Can this task start now? Returns (ok, reason, hold).
    hold = what the task is given at the start. protect=False skips the Banker's check."""
    from .resources import start_hold_for
    state = live_state()
    hold = start_hold_for(task.report_kind)
    free = state["available"]
    short = [RESOURCE_NAMES[j] for j in range(len(POOL)) if hold[j] > free[j]]
    if short:
        return False, "Not enough free resources. No free " + " or ".join(short) + " right now.", hold
    if protect:
        safe, _ = is_safe([free[j] - hold[j] for j in range(len(POOL))],
                          state["maximum"] + [need_for(task.report_kind)],
                          state["allocation"] + [hold])
        if not safe:
            return False, ("Banker's algorithm refused it. Starting this task now would leave the system "
                           "in an unsafe state, which could end in a deadlock."), hold
    return True, "", hold


def check_finish(task):
    """A task collects the rest of its need to finish. Returns (ok, reason)."""
    state = live_state()
    held = parse_held(task.held)
    need = need_for(task.report_kind)
    short = [f"{need[j] - held[j]} more {RESOURCE_NAMES[j]}" for j in range(len(POOL))
             if need[j] - held[j] > state["available"][j]]
    if short:
        return False, "It still needs " + " and ".join(short) + ", which other running tasks are holding."
    return True, ""