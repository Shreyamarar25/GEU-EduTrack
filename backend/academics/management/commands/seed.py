from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from academics.models import (Profile, Teacher, Student, Course, Enrollment, Attendance, Marks)


def make_user(username, password, role, **extra):
    user, created = User.objects.get_or_create(username=username, defaults=extra)
    if created:
        user.set_password(password)
        user.save()
    Profile.objects.get_or_create(user=user, defaults={"role": role})
    return user


class Command(BaseCommand):
    help = "Create demo users and sample academic data"

    def handle(self, *args, **opts):
        make_user("admin", "admin123", "ADMIN", is_staff=True, is_superuser=True)
        make_user("exam1", "exam123", "EXAMCELL")

        teachers = []
        for uname, name, dept in [("teacher1", "Dr. Anita Sharma", "CSE"),
                                  ("teacher2", "Mr. Rohan Verma", "CSE")]:
            u = make_user(uname, "teacher123", "TEACHER")
            t, _ = Teacher.objects.get_or_create(
                user=u, defaults={"name": name, "department": dept, "email": f"{uname}@geu.ac.in"})
            teachers.append(t)

        courses = []
        for i, (cname, cr) in enumerate([("Database Management Systems", 4), ("Operating Systems", 4),
                                         ("Computer Networks", 3), ("Machine Learning", 4)]):
            c, _ = Course.objects.get_or_create(course_name=cname, defaults={
                "credits": cr, "teacher": teachers[i % 2]})
            courses.append(c)

        students = []
        for i, name in enumerate(["Aarav Singh", "Diya Mehta", "Kabir Joshi", "Meera Nair", "Ishaan Rawat"], 1):
            roll = f"2402{1000 + i}"
            u = make_user(f"student{i}", "student123", "STUDENT")
            s, _ = Student.objects.get_or_create(user=u, defaults={
                "roll_no": roll, "name": name, "email": f"{roll}@geu.ac.in",
                "branch": "CSE", "year": 3})
            students.append(s)
            for c in courses[:3] if i % 2 else courses[1:]:
                Enrollment.objects.get_or_create(student=s, course=c)

        # a week of attendance + one exam, so reports are not empty
        for e in Enrollment.objects.all():
            for d in range(5):
                present = (e.student_id + d + e.course_id) % 4 != 0
                Attendance.objects.get_or_create(
                    student=e.student, course=e.course,
                    attendance_date=date.today() - timedelta(days=d + 1),
                    defaults={"status": "Present" if present else "Absent"})
            Marks.objects.get_or_create(
                student=e.student, course=e.course, exam_type="Mid-Term",
                defaults={"marks": 55 + (e.student_id * 7 + e.course_id * 5) % 40,
                          "exam_date": date.today() - timedelta(days=10)})
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("Logins -> admin/admin123  teacher1/teacher123  student1/student123  exam1/exam123")
