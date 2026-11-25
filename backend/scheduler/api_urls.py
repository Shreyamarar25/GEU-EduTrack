"""URLs for the deadlock + synchronization APIs. Included from academics/urls.py as path("os/", ...)."""
from django.urls import path

from . import api

urlpatterns = [
    path("sync/race/", api.RaceDemo.as_view()),
    path("sync/producer-consumer/", api.ProducerConsumerDemo.as_view()),
    path("deadlock/detect/", api.DeadlockDetect.as_view()),
    path("deadlock/safety/", api.BankersSafety.as_view()),
    path("deadlock/request/", api.BankersRequest.as_view()),
]