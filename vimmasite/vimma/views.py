from django.shortcuts import render
from rest_framework import viewsets, routers, filters
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

from vimma.models import Schedule
from vimma.perms import Perms
from vimma.util import hasPerm


class SchedulePermission(BasePermission):
    """
    Everyone can read Schedules, only users with permissions may write them.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return hasPerm(request.user, Perms.EDIT_SCHEDULE)

class ScheduleViewSet(viewsets.ModelViewSet):
    model = Schedule
    permission_classes = (IsAuthenticated, SchedulePermission,)
