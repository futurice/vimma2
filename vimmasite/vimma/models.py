from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
import json


class Permission(models.Model):
    """
    A Permission.

    There is a special omnipotent permission used to grant all permissions.
    """
    name = models.CharField(max_length=100, unique=True)


class Role(models.Model):
    """
    A role represents a set of Permissions.

    A user is assigned a set of Roles and has all permissions in those roles.
    """
    name = models.CharField(max_length=20, unique=True)
    permissions = models.ManyToManyField(Permission)


class Project(models.Model):
    """
    Projects group Users and VMs.
    """
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField()


class Profile(models.Model):
    """
    An extension of the User model.
    """
    user = models.OneToOneField(User)
    projects = models.ManyToManyField(Project)
    roles = models.ManyToManyField(Role)


def scheduleMatrixValidator(val):
    try:
        matrix = json.loads(val)
    except ValueError as e:
        raise ValidationError(e.args[0] if e.args else "Invalid JSON")
    if len(matrix) != 7:
        raise ValidationError('Schedule matrix has ' + str(len(matrix)) +
                ' rows instead of 7')
    for row in matrix:
        if len(row) != 48:
            raise ValidationError('Schedule matrix row has ' + str(len(row)) +
                    ' items instead of 48')
        for item in row:
            if type(item) != bool:
                raise ValidationError('Schedule matrix has non-bool element ' +
                        str(type(item)))

class Schedule(models.Model):
    """
    A schedule marks when the VM should be powered on or powered off.

    A 7×48 matrix with boolean values marks ON (true) or OFF (false).
    Each row is a day of the week (first row is Monday, last row is Sunday).
    Each column is a 30-min time interval. First column is [0:00, 0:30),
    second is [0:30, 1:00), last column is [23:30, 24:00).

    Since a schedule only deals with local time, anyone using it must create a
    local time (e.g. a timezone-aware VM) then check it against the schedule
    to find ON or OFF state.
    """
    name = models.CharField(max_length=50, unique=True)
    matrix = models.TextField(validators=[scheduleMatrixValidator])
    # ‘special’ schedules can't be used by anyone. E.g. 24h turned on.
    # Users need the USE_SPECIAL_SCHEDULE permission to use them.
    isSpecial = models.BooleanField(default=False)
    # TODO: find a way to mark a schedule as ‘default’, to pre-select it in the
    # UI. Either a BooleanField or a singleton with a ForeignKey to Schedule.
