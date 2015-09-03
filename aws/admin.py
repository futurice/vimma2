from django.contrib import admin

from aws.models import (
    AWSProvider, AWSVMConfig, AWSVM, AWSAudit, AWSPowerLog,
)


for model in (
    AWSProvider, AWSVMConfig, AWSVM, AWSAudit, AWSPowerLog,
    ):
    admin.site.register(model)
