from django.core.management.base import BaseCommand

from academics.models import OsProcess

# (task name, task type, arrival time, burst time, priority)  - priority 1 = most urgent
SAMPLE = [
    ("Attendance report - CSE branch",   "ATTENDANCE_REPORT", 0, 6, 2),
    ("Exam results report - Mid-Term",   "MARKS_REPORT",      1, 8, 1),
    ("Full student report - Aarav Singh", "STUDENT_REPORT",   2, 3, 3),
    ("Course summary - DBMS",            "COURSE_SUMMARY",    3, 4, 2),
    ("Low-attendance notifications",     "NOTIFICATION",      5, 2, 3),
    ("Marks report - Operating Systems", "MARKS_REPORT",      6, 5, 1),
]


class Command(BaseCommand):
    help = "Fill the os_process table with sample system tasks for the scheduler"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="delete existing processes first")

    def handle(self, *args, **opts):
        if opts["reset"]:
            OsProcess.objects.all().delete()
        if OsProcess.objects.exists():
            self.stdout.write("os_process already has rows. Use --reset to replace them.")
            return
        for name, kind, arrival, burst, prio in SAMPLE:
            OsProcess.objects.create(task_name=name, task_type=kind, arrival_time=arrival,
                                     burst_time=burst, priority=prio, state="READY")
        self.stdout.write(self.style.SUCCESS(f"{len(SAMPLE)} processes added to os_process."))