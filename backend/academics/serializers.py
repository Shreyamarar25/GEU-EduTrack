from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from .models import (Profile, Teacher, Student, Course, Enrollment,
                     Attendance, Marks, OsProcess)


def _make_login(role, username, password, email):
    if User.objects.filter(username=username).exists():
        raise serializers.ValidationError({"username": "This username already exists."})
    user = User.objects.create_user(username=username, password=password, email=email)
    Profile.objects.create(user=user, role=role)
    return user


class StudentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Student
        fields = ["student_id", "roll_no", "name", "email", "phone", "branch", "year",
                  "username", "password"]

    @transaction.atomic
    def create(self, data):
        username = data.pop("username", None) or data["roll_no"]
        password = data.pop("password", None) or "student123"
        user = _make_login("STUDENT", username, password, data.get("email", ""))
        return Student.objects.create(user=user, **data)


class TeacherSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Teacher
        fields = ["teacher_id", "name", "department", "email", "phone", "username", "password"]

    @transaction.atomic
    def create(self, data):
        username = data.pop("username", None) or data["email"].split("@")[0]
        password = data.pop("password", None) or "teacher123"
        user = _make_login("TEACHER", username, password, data.get("email", ""))
        return Teacher.objects.create(user=user, **data)


class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source="teacher.name", read_only=True, default=None)

    class Meta:
        model = Course
        fields = ["course_id", "course_name", "credits", "teacher", "teacher_name"]


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    roll_no = serializers.CharField(source="student.roll_no", read_only=True)
    course_name = serializers.CharField(source="course.course_name", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["enrollment_id", "student", "student_name", "roll_no", "course",
                  "course_name", "enrollment_date", "status"]
        read_only_fields = ["enrollment_date"]


class _EnrolledCheck:
    """Shared rule: attendance/marks only for students enrolled in that course."""

    def validate(self, data):
        student = data.get("student") or getattr(self.instance, "student", None)
        course = data.get("course") or getattr(self.instance, "course", None)
        if not Enrollment.objects.filter(student=student, course=course).exists():
            raise serializers.ValidationError("This student is not enrolled in this course.")
        return data


class AttendanceSerializer(_EnrolledCheck, serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    course_name = serializers.CharField(source="course.course_name", read_only=True)

    class Meta:
        model = Attendance
        fields = ["attendance_id", "student", "student_name", "course", "course_name",
                  "attendance_date", "status"]


class MarksSerializer(_EnrolledCheck, serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    course_name = serializers.CharField(source="course.course_name", read_only=True)

    class Meta:
        model = Marks
        fields = ["mark_id", "student", "student_name", "course", "course_name",
                  "exam_type", "marks", "exam_date"]

    def validate_marks(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Marks must be between 0 and 100.")
        return value


class OsProcessSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source="requested_by.username", read_only=True, default=None)

    class Meta:
        model = OsProcess
        fields = "__all__"


class ReportRequestSerializer(serializers.ModelSerializer):
    """What a requester sees for their own request: Waiting (READY) or Approved (COMPLETED)."""
    status = serializers.SerializerMethodField()
    can_download = serializers.SerializerMethodField()

    class Meta:
        model = OsProcess
        fields = ["process_id", "task_name", "report_kind", "report_student", "priority",
                  "state", "status", "can_download", "completion_time", "waiting_time",
                  "turnaround_time"]

    def get_status(self, obj):
        return "Approved" if obj.state == "COMPLETED" else "Waiting"

    def get_can_download(self, obj):
        return obj.state == "COMPLETED"
