from django.contrib import admin

from aws.models import (
    AWSProvider, AWSVMConfig, AWSVM, AWSAudit, AWSPowerLog, AWSVMExpiration, AWSFirewallRule, AWSFirewallRuleExpiration,
)


for model in (
    AWSProvider, AWSVMConfig, AWSVM, AWSAudit, AWSPowerLog, AWSVMExpiration, AWSFirewallRule, AWSFirewallRuleExpiration,
    ):
    admin.site.register(model)
