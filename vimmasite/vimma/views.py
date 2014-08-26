from django.shortcuts import render
from rest_framework import viewsets, routers, filters
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

from vimma.models import Schedule
from vimma.perms import Perms
from vimma.util import has_perm, login_required_or_forbidden


class SchedulePermission(BasePermission):
    """
    Everyone can read Schedules, only users with permissions may write them.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return has_perm(request.user, Perms.EDIT_SCHEDULE)

class ScheduleViewSet(viewsets.ModelViewSet):
    model = Schedule
    permission_classes = (IsAuthenticated, SchedulePermission,)
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name',)


@login_required_or_forbidden
def index(request):
    """
    Homepage.
    """
    return render(request, 'vimma/index.html')


@login_required_or_forbidden
def test(request):
    """
    JavaScript Unit Tests.
    """
    return render(request, 'vimma/test.html')
