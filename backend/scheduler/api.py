"""APIs for the deadlock and synchronization pages (Admin only)."""
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.permissions import RolePermission
from . import deadlock, synchronization


def _int(value, name, low, high):
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Enter a whole number."})
    if not low <= v <= high:
        raise ValidationError({name: f"Use a number from {low} to {high}."})
    return v


def _matrix(data, name):
    try:
        mat = [[int(x) for x in row] for row in data]
    except (TypeError, ValueError):
        raise ValidationError({name: "Use whole numbers only."})
    if any(x < 0 for row in mat for x in row):
        raise ValidationError({name: "Numbers cannot be negative."})
    return mat


def _vector(data, name):
    return _matrix([data], name)[0]


class AdminOnly(APIView):
    permission_classes = [RolePermission]
    read_roles = ["ADMIN"]
    write_roles = ["ADMIN"]


class RaceDemo(AdminOnly):
    def post(self, request):
        d = request.data
        return Response(synchronization.race_demo(
            workers=_int(d.get("workers", 4), "workers", 2, 8),
            increments=_int(d.get("increments", 200), "increments", 10, 500),
            use_mutex=bool(d.get("use_mutex"))))


class ProducerConsumerDemo(AdminOnly):
    def post(self, request):
        d = request.data
        return Response(synchronization.producer_consumer(
            producers=_int(d.get("producers", 2), "producers", 1, 5),
            consumers=_int(d.get("consumers", 1), "consumers", 1, 3),
            items=_int(d.get("items", 4), "items", 1, 6),
            capacity=_int(d.get("capacity", 3), "capacity", 1, 6)))


class DeadlockDetect(AdminOnly):
    def post(self, request):
        d = request.data
        try:
            return Response(deadlock.detect(_matrix(d.get("allocation"), "allocation"),
                                            _matrix(d.get("request"), "request"),
                                            _vector(d.get("available"), "available")))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})


class BankersSafety(AdminOnly):
    def post(self, request):
        d = request.data
        try:
            return Response(deadlock.bankers_safety(_vector(d.get("available"), "available"),
                                                    _matrix(d.get("maximum"), "maximum"),
                                                    _matrix(d.get("allocation"), "allocation")))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})


class BankersRequest(AdminOnly):
    def post(self, request):
        d = request.data
        try:
            return Response(deadlock.bankers_request(
                _vector(d.get("available"), "available"), _matrix(d.get("maximum"), "maximum"),
                _matrix(d.get("allocation"), "allocation"),
                _int(d.get("process"), "process", 0, 50), _vector(d.get("request"), "request")))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})