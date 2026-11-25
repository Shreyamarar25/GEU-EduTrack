"""Shared resources that report tasks need while they run (used by the deadlock logic)."""

# The shared things. This order is used in every list of numbers in the deadlock code.
RESOURCE_NAMES = ["PDF engine", "DB connection", "Table lock"]

# How many of each the system has in total.
POOL = [3, 3, 2]



# The most of each resource a report type can ever need (its "maximum claim").
# Same order as RESOURCE_NAMES: PDF engine, DB connection, Table lock.
NEEDS = {
    "attendance": [1, 1, 1],
    "performance": [1, 2, 1],
    "student": [2, 1, 2],
}


def need_for(report_type):
    """Maximum claim of a report type. Sample tasks without a report type get a small default."""
    return NEEDS.get(report_type, [1, 1, 1])



# What a task is given the moment it starts. It collects the rest of its need when it finishes.
START_HOLD = {
    "attendance": [1, 0, 1],
    "performance": [1, 1, 1],
    "student": [1, 0, 1],
}


def start_hold_for(report_type):
    """What a task holds from the moment it starts. Sample tasks get one PDF engine."""
    return START_HOLD.get(report_type, [1, 0, 0])