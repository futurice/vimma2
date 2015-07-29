from django.contrib.auth.middleware import RemoteUserMiddleware
import os

class CustomHeaderMiddleware(RemoteUserMiddleware):
    header = os.getenv('REMOTE_USER_HEADER', 'REMOTE_USER')
