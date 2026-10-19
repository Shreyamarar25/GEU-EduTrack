from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Avg, Count, Max, Q
from rest_framework import filters, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduler.scheduler import schedule, ALGORITHMS
from django.http import HttpResponse
from django.utils import timezone
from . import pdf_reports
from .models import (Teacher, Student, Course, Enrollment, Attendance, Marks, OsProcess)
from .permissions import RolePermission, get_role
from .serializers import (StudentSerializer, TeacherSerializer, CourseSerializer,
                          EnrollmentSerializer, AttendanceSerializer, MarksSerializer,
                          OsProcessSerializer, ReportRequestSerializer)

ADMIN, TEACHER, STUDENT, EXAM = "ADMIN", "TEACHER", "STUDENT", "EXAMCELL"


# ---------------------------------------------------------------- auth
@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    user = authenticate(username=request.data.get("username"), password=request.data.get("password"))
    if not user:
        return Response({"detail": "Invalid username or password."}, status=400)
    token, _ = Token.objects.get_or_create(user=user)
    name = user.get_full_name() or user.username
    for model in (Student, Teacher):
        person = model.objects.filter(user=user).first()
        if person:
            name = person.name
    return Response({"token": token.key, "role": get_role(user), "name": name})


# ------------------------------------------------------------ helpers
def my_student(user):
    return Student.objects.filter(user=user).first()


def scope(qs, user, teacher_path, student_path="student__user"):
    """Students see only their own rows, teachers only rows of their own courses."""
    role = get_role(user)
    if role == STUDENT:
        return qs.filter(**{student_path: user})
    if role == TEACHER:
        return qs.filter(**{teacher_path: user})
    return qs


class RoleViewSet(viewsets.ModelViewSet):
    permission_classes = [RolePermission]
    read_roles = None
    write_roles = [ADMIN]


# --------------------------------------------------------- CRUD views
class StudentViewSet(RoleViewSet):
    serializer_class = StudentSerializer
    read_roles = [ADMIN, TEACHER, EXAM, STUDENT]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "roll_no", "email", "branch"]

    def get_queryset(self):
        qs = Student.objects.order_by("roll_no")
        if get_role(self.request.user) == STUDENT:
            qs = qs.filter(user=self.request.user)
        return qs

    def perform_destroy(self, instance):
        (instance.user or instance).delete()  # deleting the login cascades to the student


class TeacherViewSet(RoleViewSet):
    serializer_class = TeacherSerializer
    read_roles = [ADMIN, TEACHER]
    queryset = Teacher.objects.order_by("name")

    def perform_destroy(self, instance):
        (instance.user or instance).delete()


class CourseViewSet(RoleViewSet):
    serializer_class = CourseSerializer
    read_roles = None  # every logged-in role may read

    def get_queryset(self):
        qs = Course.objects.select_related("teacher").order_by("course_name")
        role = get_role(self.request.user)
        if role == TEACHER:
            qs = qs.filter(teacher__user=self.request.user)
        elif role == STUDENT:
            qs = qs.filter(enrollment__student__user=self.request.user)
        return qs


class EnrollmentViewSet(RoleViewSet):
    serializer_class = EnrollmentSerializer
    read_roles = [ADMIN, TEACHER, STUDENT, EXAM]  # exam cell needs it to pick student+course for marks
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = Enrollment.objects.select_related("student", "course")
        return scope(qs, self.request.user, "course__teacher__user")

    @transaction.atomic  # enrollment is all-or-nothing
    def perform_create(self, serializer):
        serializer.save()


class AttendanceViewSet(RoleViewSet):
    serializer_class = AttendanceSerializer
    read_roles = [ADMIN, TEACHER, STUDENT]
    write_roles = [ADMIN, TEACHER]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        qs = Attendance.objects.select_related("student", "course").order_by("-attendance_date")
        qs = scope(qs, self.request.user, "course__teacher__user")
        p = self.request.query_params
        if p.get("course"):
            qs = qs.filter(course_id=p["course"])
        if p.get("student"):
            qs = qs.filter(student_id=p["student"])
        if p.get("date"):
            qs = qs.filter(attendance_date=p["date"])
        return qs

    def _check_teacher_owns(self, course):
        user = self.request.user
        if get_role(user) == TEACHER and (not course.teacher or course.teacher.user_id != user.id):
            raise PermissionDenied("You can only mark attendance for your own courses.")

    def perform_create(self, serializer):
        self._check_teacher_owns(serializer.validated_data["course"])
        serializer.save()

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        """Mark a whole class at once: {course, date, records:[{student, status}]}"""
        try:
            course = Course.objects.get(pk=request.data.get("course"))
        except Course.DoesNotExist:
            raise ValidationError({"course": "Course not found."})
        self._check_teacher_owns(course)
        date, records = request.data.get("date"), request.data.get("records") or []
        if not date or not records:
            raise ValidationError("date and records are required.")
        enrolled = set(Enrollment.objects.filter(course=course).values_list("student_id", flat=True))
        with transaction.atomic():
            for r in records:
                if int(r["student"]) not in enrolled:
                    raise ValidationError(f"Student {r['student']} is not enrolled in this course.")
                if r["status"] not in ("Present", "Absent"):
                    raise ValidationError("status must be Present or Absent.")
                Attendance.objects.update_or_create(
                    student_id=r["student"], course=course, attendance_date=date,
                    defaults={"status": r["status"]})
        return Response({"saved": len(records)})


class MarksViewSet(RoleViewSet):
    serializer_class = MarksSerializer
    read_roles = [ADMIN, TEACHER, STUDENT, EXAM]
    write_roles = [ADMIN, TEACHER, EXAM]

    def get_queryset(self):
        qs = Marks.objects.select_related("student", "course").order_by("-exam_date")
        qs = scope(qs, self.request.user, "course__teacher__user")
        p = self.request.query_params
        if p.get("course"):
            qs = qs.filter(course_id=p["course"])
        if p.get("student"):
            qs = qs.filter(student_id=p["student"])
        return qs

    def _check(self, course):
        user = self.request.user
        if get_role(user) == TEACHER and (not course.teacher or course.teacher.user_id != user.id):
            raise PermissionDenied("You can only enter marks for your own courses.")

    def perform_create(self, serializer):
        self._check(serializer.validated_data["course"])
        serializer.save()

    def perform_update(self, serializer):
        self._check(serializer.instance.course)
        serializer.save()


class OsProcessViewSet(RoleViewSet):
    """The os_process table: the Admin can list, add and delete queue rows."""
    serializer_class = OsProcessSerializer
    read_roles = [ADMIN]
    queryset = OsProcess.objects.order_by("process_id")


# ------------------------------------------------------------ reports
def _enrollments_for(user):
    qs = Enrollment.objects.select_related("student", "course")
    return scope(qs, user, "course__teacher__user")


class AttendanceReport(APIView):
    """Attendance % per student per course (GROUP BY + aggregate)."""
    permission_classes = [RolePermission]
    read_roles = [ADMIN, TEACHER, STUDENT]
    write_roles = []

    def get(self, request):
        stats = {(r["student"], r["course"]): r for r in
                 Attendance.objects.values("student", "course").annotate(
                     total=Count("attendance_id"),
                     present=Count("attendance_id", filter=Q(status="Present")))}
        rows = []
        for e in _enrollments_for(request.user):
            s = stats.get((e.student_id, e.course_id), {"total": 0, "present": 0})
            pct = round(100 * s["present"] / s["total"], 1) if s["total"] else None
            rows.append({"roll_no": e.student.roll_no, "student_name": e.student.name,
                         "course_name": e.course.course_name, "total_classes": s["total"],
                         "present": s["present"], "percentage": pct,
                         "low": pct is not None and pct < 75})
        return Response(rows)


class PerformanceReport(APIView):
    """Average marks per student per course."""
    permission_classes = [RolePermission]
    read_roles = [ADMIN, TEACHER, STUDENT, EXAM]
    write_roles = []

    def get(self, request):
        role = get_role(request.user)
        enrollments = Enrollment.objects.select_related("student", "course")
        enrollments = scope(enrollments, request.user, "course__teacher__user")
        stats = {(r["student"], r["course"]): r for r in
                 Marks.objects.values("student", "course").annotate(
                     avg=Avg("marks"), exams=Count("mark_id"))}
        rows = []
        for e in enrollments:
            s = stats.get((e.student_id, e.course_id))
            avg = round(float(s["avg"]), 2) if s else None
            rows.append({"roll_no": e.student.roll_no, "student_name": e.student.name,
                         "course_name": e.course.course_name, "exams": s["exams"] if s else 0,
                         "average": avg})
        return Response(rows)


class Stats(APIView):
    """Numbers for the overview cards."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = get_role(request.user)
        if role in (ADMIN, EXAM):
            cards = {"Students": Student.objects.count(), "Teachers": Teacher.objects.count(),
                     "Courses": Course.objects.count(), "Enrollments": Enrollment.objects.count()}
        elif role == TEACHER:
            en = _enrollments_for(request.user)
            cards = {"My courses": Course.objects.filter(teacher__user=request.user).count(),
                     "My students": en.values("student").distinct().count()}
        else:
            en = _enrollments_for(request.user)
            att = Attendance.objects.filter(student__user=request.user)
            total = att.count()
            pct = round(100 * att.filter(status="Present").count() / total, 1) if total else 0
            avg = Marks.objects.filter(student__user=request.user).aggregate(a=Avg("marks"))["a"]
            cards = {"Enrolled courses": en.count(), "Attendance %": pct,
                     "Average marks": round(float(avg), 1) if avg is not None else 0}
        return Response({"role": role, "cards": cards})


# ---------------------------------------------------------- scheduler
class SimulateScheduler(APIView):
    """POST {algorithm, processes:[{pid, arrival, burst, priority}]} -> CT/WT/TAT + Gantt.
    Works on the data sent in the request (not stored in os_process)."""
    permission_classes = [RolePermission]
    read_roles = [ADMIN]
    write_roles = [ADMIN]

    def post(self, request):
        algo = str(request.data.get("algorithm", "FCFS")).upper()
        if algo not in ALGORITHMS:
            raise ValidationError({"algorithm": f"Use one of {ALGORITHMS}"})
        try:
            return Response(schedule(request.data.get("processes") or [], algo))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})


# ------------------------------------------------- report data + PDF helpers
def attendance_rows(user):
    stats = {(r["student"], r["course"]): r for r in
             Attendance.objects.values("student", "course").annotate(
                 total=Count("attendance_id"),
                 present=Count("attendance_id", filter=Q(status="Present")))}
    rows = []
    for e in _enrollments_for(user):
        s = stats.get((e.student_id, e.course_id), {"total": 0, "present": 0})
        pct = round(100 * s["present"] / s["total"], 1) if s["total"] else None
        rows.append({"student_id": e.student_id, "roll_no": e.student.roll_no,
                     "student_name": e.student.name,
                     "course_name": e.course.course_name, "total_classes": s["total"],
                     "present": s["present"], "percentage": pct,
                     "low": pct is not None and pct < 75})
    return rows


def performance_rows(user):
    enrollments = scope(Enrollment.objects.select_related("student", "course"),
                        user, "course__teacher__user")
    stats = {(r["student"], r["course"]): r for r in
             Marks.objects.values("student", "course").annotate(
                 avg=Avg("marks"), exams=Count("mark_id"))}
    rows = []
    for e in enrollments:
        s = stats.get((e.student_id, e.course_id))
        rows.append({"student_id": e.student_id, "roll_no": e.student.roll_no,
                     "student_name": e.student.name, "course_name": e.course.course_name,
                     "exams": s["exams"] if s else 0,
                     "average": round(float(s["avg"]), 2) if s else None})
    return rows


# Priority comes from the requester's role. 1 = most urgent.
ROLE_PRIORITY = {EXAM: 1, ADMIN: 2, TEACHER: 3, STUDENT: 4}
# Fixed burst time (scheduler time units) for each report type.
REPORT_BURST = {"student": 3, "performance": 5, "attendance": 6}
REPORT_TITLE = {"attendance": "Attendance report", "performance": "Performance report",
                "student": "Full student report"}


def authorize_report(user, kind, student_id=None):
    """Raises if this user may not have this report.
    Returns the Student for a 'student' report, otherwise None."""
    role = get_role(user)
    if kind == "attendance":
        if role == EXAM:
            raise PermissionDenied("Exam Cell cannot download attendance reports.")
        return None
    if kind == "performance":
        return None
    if kind == "student":
        allowed = _enrollments_for(user).filter(student_id=student_id)
        student = Student.objects.filter(pk=student_id).first()
        if not student or (role != ADMIN and role != EXAM and not allowed.exists()
                           and not (role == STUDENT and student.user_id == user.id)):
            raise PermissionDenied("You cannot download this student's report.")
        return student
    raise ValidationError("Unknown report type.")


def build_report(user, kind, student_id=None):
    """Checks permission, then generates the PDF. Returns (pdf_bytes, filename)."""
    role = get_role(user)
    student = authorize_report(user, kind, student_id)
    if kind == "attendance":
        return pdf_reports.attendance_pdf(attendance_rows(user), user), "attendance_report.pdf"
    if kind == "performance":
        return pdf_reports.performance_pdf(performance_rows(user), user), "performance_report.pdf"
    att = [r for r in attendance_rows(user) if r["student_id"] == student.student_id] \
        if role != EXAM else []
    perf = [r for r in performance_rows(user) if r["student_id"] == student.student_id]
    marks = Marks.objects.filter(student=student).select_related("course").order_by("course__course_name")
    if role == TEACHER:
        marks = marks.filter(course__teacher__user=user)
    return (pdf_reports.student_pdf(student, att, perf, list(marks), user),
            f"student_report_{student.roll_no}.pdf")


def _pdf_response(pdf, name):
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{name}"'
    resp["Access-Control-Expose-Headers"] = "Content-Disposition"
    return resp


# ------------------------------------------------ report download requests
class ReportRequestCreate(APIView):
    """POST {kind: attendance|performance|student, student_id?}
    Admin: gets the PDF instantly. Everyone else: a READY row is added to os_process
    and the request waits for the Admin to run the scheduler."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        kind = request.data.get("kind")
        student_id = request.data.get("student_id")
        role = get_role(request.user)

        if role == ADMIN:  # the Admin is the approver, so no waiting
            pdf, name = build_report(request.user, kind, student_id)
            return _pdf_response(pdf, name)

        student = authorize_report(request.user, kind, student_id)  # reject bad requests now

        # Same report asked again while it is still waiting -> return the existing request
        dup = OsProcess.objects.filter(requested_by=request.user, report_kind=kind,
                                       report_student=student, state="READY").first()
        if dup:
            return Response(ReportRequestSerializer(dup).data, status=200)

        # Arrival time = order in which requests were clicked (0, 1, 2, ...)
        last = OsProcess.objects.filter(state="READY").aggregate(m=Max("arrival_time"))["m"]
        title = REPORT_TITLE[kind] + (f" - {student.name}" if student else "")
        proc = OsProcess.objects.create(
            task_name=f"{title} ({request.user.username}, {role})",
            task_type=f"{kind.upper()}_REPORT",
            arrival_time=0 if last is None else last + 1,
            burst_time=REPORT_BURST[kind],
            priority=ROLE_PRIORITY.get(role, 4),
            state="READY",
            requested_by=request.user, report_kind=kind, report_student=student)
        return Response(ReportRequestSerializer(proc).data, status=201)


class MyReportRequests(APIView):
    """GET -> the logged-in user's own requests, each marked Waiting or Approved."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = OsProcess.objects.filter(requested_by=request.user).order_by("-process_id")
        return Response(ReportRequestSerializer(qs, many=True).data)


class ReportRequestDownload(APIView):
    """GET -> the PDF, only for the requester and only after the request is approved."""
    permission_classes = [IsAuthenticated]

    def get(self, request, process_id):
        proc = OsProcess.objects.filter(pk=process_id, requested_by=request.user).first()
        if not proc:
            raise PermissionDenied("This is not your request.")
        if proc.state != "COMPLETED":
            raise PermissionDenied("Not approved yet. The Admin has not approved this request.")
        pdf, name = build_report(request.user, proc.report_kind, proc.report_student_id)
        return _pdf_response(pdf, name)


# ------------------------------------------------------- run / reset scheduler
class RunScheduler(APIView):
    """POST {algorithm} -> runs the algorithm on every waiting (READY) request, but approves
    only the ONE it schedules first: that row becomes COMPLETED and saves its CT/WT/TAT.
    The others stay READY until the next click."""
    permission_classes = [RolePermission]
    read_roles = [ADMIN]
    write_roles = [ADMIN]

    def post(self, request):
        algo = str(request.data.get("algorithm", "FCFS")).upper()
        if algo not in ALGORITHMS:
            raise ValidationError({"algorithm": f"Use one of {ALGORITHMS}"})
        procs = list(OsProcess.objects.filter(state="READY").order_by("arrival_time", "process_id"))
        if not procs:
            raise ValidationError({"detail": "No waiting requests in the queue."})

        # The Admin clicks when every request is already waiting, so all of them are "here" at time 0.
        # Clicked order still breaks ties (FCFS order, equal burst, equal priority).
        data = [{"pid": f"P{p.process_id}", "arrival": 0,
                 "burst": p.burst_time, "priority": p.priority} for p in procs]
        names = {f"P{p.process_id}": p.task_name for p in procs}

        comparison = []
        for a in ALGORITHMS:
            o = schedule(data, a)
            comparison.append({"algorithm": a, "avg_waiting": o["avg_waiting"],
                               "avg_turnaround": o["avg_turnaround"]})
        out = schedule(data, algo)
        for r in out["results"]:
            r["task_name"] = names[r["pid"]]

        # the request the algorithm runs first = the one that completes first
        first = min(out["results"], key=lambda r: r["completion"])
        OsProcess.objects.filter(pk=int(first["pid"][1:])).update(
            state="COMPLETED", completion_time=first["completion"],
            waiting_time=first["waiting"], turnaround_time=first["turnaround"],
            approved_at=timezone.now())

        out["approved"] = {"pid": first["pid"], "task_name": first["task_name"]}
        out["comparison"] = comparison
        return Response(out)


class ResetScheduler(APIView):
    """POST -> puts every process back to READY and clears CT/WT/TAT and the approval time."""
    permission_classes = [RolePermission]
    read_roles = [ADMIN]
    write_roles = [ADMIN]

    def post(self, request):
        n = OsProcess.objects.update(state="READY", completion_time=None,
                                     waiting_time=None, turnaround_time=None,
                                     approved_at=None)
        return Response({"reset": n})