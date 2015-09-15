from django.contrib import admin
from django.db import models

from vimma.tools import get_types

models = get_types('aws.models', models.Model)

for model in models:
    admin.site.register(model)
