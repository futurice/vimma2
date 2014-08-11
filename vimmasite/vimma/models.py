from django.contrib.auth.models import User
from django.db import models


class Project(models.Model):
    """
    Projects group Users and VMs.
    """
    name = models.CharField(max_length=100)
    email = models.EmailField()


class Profile(models.Model):
    """
    An extension of the User model.
    """
    user = models.OneToOneField(User)
    projects = models.ManyToManyField(Project)
