from django.contrib import admin
from django.db import models

from vimma.tools import get_types

models = get_types('vimma.models', models.Model, p=lambda x: not x._meta.abstract)

for model in models:
    admin.site.register(model)
