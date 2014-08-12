"""
Settings file used for running tests.
"""

from vimmasite.settings import *

# Other workarounds, such as self.client.login(remote_user='username') or
# Django-REST-Framework's APIClient did't work with Django-REST-Framework.
del AUTHENTICATION_BACKENDS
