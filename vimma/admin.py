from django.contrib import admin

from vimma.models import (
    TimeZone, Permission,
    Role, User, Project,
    Provider, VMConfig, VM,
)


for model in (
        TimeZone, Permission,
        Role, User, Project,
        Provider, VMConfig, VM,
        ):
    admin.site.register(model)
