from django.contrib.auth.models import User
from django.db import models


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
