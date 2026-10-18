from django.contrib import admin
from .models import Profile, Teacher, Student, Course, Enrollment, Attendance, Marks, OsProcess

for m in (Profile, Teacher, Student, Course, Enrollment, Attendance, Marks, OsProcess):
    admin.site.register(m)
