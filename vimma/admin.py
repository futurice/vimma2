from django.contrib import admin

from vimma.models import (
    TimeZone, Permission, Schedule,
    Role, User, Project,
)


for model in (
        TimeZone, Permission, Schedule,
        Role, User, Project,
        ):
    admin.site.register(model)
