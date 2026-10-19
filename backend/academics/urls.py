from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("students", views.StudentViewSet, basename="student")
router.register("teachers", views.TeacherViewSet, basename="teacher")
router.register("courses", views.CourseViewSet, basename="course")
router.register("enrollments", views.EnrollmentViewSet, basename="enrollment")
router.register("attendance", views.AttendanceViewSet, basename="attendance")
router.register("marks", views.MarksViewSet, basename="marks")
router.register("processes", views.OsProcessViewSet, basename="process")

urlpatterns = [
    path("auth/login/", views.login),
    path("stats/", views.Stats.as_view()),
    path("reports/attendance/", views.AttendanceReport.as_view()),
    path("reports/performance/", views.PerformanceReport.as_view()),
    path("reports/request/", views.ReportRequestCreate.as_view()),
    path("reports/requests/", views.MyReportRequests.as_view()),
    path("reports/requests/<int:process_id>/download/", views.ReportRequestDownload.as_view()),
    path("scheduler/run/", views.RunScheduler.as_view()),
    path("scheduler/reset/", views.ResetScheduler.as_view()),
    path("scheduler/simulate/", views.SimulateScheduler.as_view()),
    path("", include(router.urls)),
]
