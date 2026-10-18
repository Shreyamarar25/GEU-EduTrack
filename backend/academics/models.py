from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """Stores the role of every login user."""
    ROLES = [("ADMIN", "Admin"), ("TEACHER", "Teacher"),
             ("STUDENT", "Student"), ("EXAMCELL", "Exam Cell")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLES)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Teacher(models.Model):
    teacher_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)

    class Meta:
        db_table = "teacher"

    def __str__(self):
        return self.name


class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    roll_no = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    branch = models.CharField(max_length=50)
    year = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "student"
        indexes = [models.Index(fields=["name"], name="idx_student_name")]  # fast search

    def __str__(self):
        return f"{self.roll_no} - {self.name}"


class Course(models.Model):
    course_id = models.AutoField(primary_key=True)
    course_name = models.CharField(max_length=100)
    credits = models.PositiveSmallIntegerField()
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "course"

    def __str__(self):
        return self.course_name


class Enrollment(models.Model):
    enrollment_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrollment_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, default="Active")

    class Meta:
        db_table = "enrollment"
        unique_together = ("student", "course")


class Attendance(models.Model):
    STATUS = [("Present", "Present"), ("Absent", "Absent")]
    attendance_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    attendance_date = models.DateField()
    status = models.CharField(max_length=7, choices=STATUS)

    class Meta:
        db_table = "attendance"
        unique_together = ("student", "course", "attendance_date")  # no duplicate entry
        indexes = [models.Index(fields=["student", "attendance_date"], name="idx_att_student_date")]


class Marks(models.Model):
    EXAMS = [("Quiz", "Quiz"), ("Assignment", "Assignment"),
             ("Mid-Term", "Mid-Term"), ("End-Term", "End-Term")]
    mark_id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exam_type = models.CharField(max_length=20, choices=EXAMS)
    marks = models.DecimalField(max_digits=5, decimal_places=2)
    exam_date = models.DateField()

    class Meta:
        db_table = "marks"
        unique_together = ("student", "course", "exam_type")


class OsProcess(models.Model):
    """System tasks (report generation, notifications...) that the OS scheduler will process.
    Phase 2: table + API exist. Reading/writing it from the scheduler = Phase 3 (OS-DBMS integration)."""
    STATES = [("NEW", "NEW"), ("READY", "READY"), ("RUNNING", "RUNNING"), ("COMPLETED", "COMPLETED")]
    process_id = models.AutoField(primary_key=True)
    task_name = models.CharField(max_length=100)
    task_type = models.CharField(max_length=50, default="REPORT")
    arrival_time = models.PositiveIntegerField(default=0)
    burst_time = models.PositiveIntegerField()
    priority = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=10, choices=STATES, default="NEW")
    completion_time = models.IntegerField(null=True, blank=True)
    waiting_time = models.IntegerField(null=True, blank=True)
    turnaround_time = models.IntegerField(null=True, blank=True)
    # Report-download requests: who asked and which report (blank for ordinary tasks)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="report_requests")
    report_kind = models.CharField(max_length=20, blank=True)  # attendance / performance / student
    report_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)  # when the Admin's run approved it

    class Meta:
        db_table = "os_process"