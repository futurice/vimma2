import datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.timezone import utc
from django.contrib.contenttypes.models import ContentType

import json
import pytz
from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)
import sys
import traceback

from vimma import vmutil
from vimma.actions import Actions
from vimma.audit import Auditor
import vimma.expiry
from vimma.models import (
    Schedule, TimeZone, Project,
    User, VM, Provider,
    Audit, Expiration, Expiration,
    FirewallRule, FirewallRuleExpiration,
)

from vimma.util import (
    can_do, login_required_or_forbidden, get_http_json_err,
    retry_in_transaction,
)
from vimmasite.pagination import VimmaPagination

from aws.models import FirewallRule

aud = Auditor(__name__)

@login_required_or_forbidden
def index(request):
    return render(request, 'vimma/index.html')

aws_firewall_rule_protocol_choices_json = json.dumps([
    {'value': c[0], 'label': c[1]}
    for c in FirewallRule.IP_PROTOCOL_CHOICES])

audit_levels_json = json.dumps([{'id': c[0], 'name': c[1]}
    for c in Audit.LEVEL_CHOICES])

@login_required_or_forbidden
def base_js(request):
    """
    base.js, included by the html template(s).
    """
    return render(request, 'vimma/base.js', {
        'providers': json.dumps(list(Provider.choices().keys())),
        'pagination': VimmaPagination,
        'audit_level_choices_json': audit_levels_json,
        'aws_firewall_rule_protocol_choices_json':
        aws_firewall_rule_protocol_choices_json,
    }, content_type='application/javascript; charset=utf-8')


# Allow unauthenticated access in order to easily test with browser automation
#@login_required_or_forbidden
def test(request):
    """
    JavaScript Unit Tests.
    """
    return render(request, 'vimma/test.html')

