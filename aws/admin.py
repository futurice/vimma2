from django.contrib import admin

from aws.models import (
    AWSProvider, AWSVMConfig, AWSVM,
)


for model in (
    AWSProvider, AWSVMConfig, AWSVM,
    ):
    admin.site.register(model)
