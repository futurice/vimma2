from django import template
from django.conf import settings
from django.template.loader import render_to_string, get_template
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.contrib.sites.models import get_current_site
from django.shortcuts import get_object_or_404
from django.db.models.fields import FieldDoesNotExist

from datetime import datetime
from math import ceil

#from vmm.common.assets import assets as assetgen
from vmm.assets import assets as assetgen

register = template.Library()

@register.simple_tag() # used outside of templates
def assets(path):
    return assetgen(path)
