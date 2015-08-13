from django.contrib import admin

from vimma.models import (
    TimeZone, Permission,
    Role, User, Project
)


for model in (
        TimeZone, Permission,
        Role, User, Project
        ):
    admin.site.register(model)
