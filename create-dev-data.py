from vimma.util import create_vimma_user
from vimma.models import Schedule, Role, Permission
from vimma.perms import Perms
import json

create_vimma_user('u1', 'u1@example.com', 'pass')
Schedule.objects.create(name='My Schedule',
        matrix=json.dumps(7*[10*2*[False] + 8*2*[True] + 6*2*[False]])
        ).full_clean()

u2 = create_vimma_user('u2', 'u2@example.com', 'pass')
r = Role.objects.create(name='omnipotent')
p = Permission.objects.create(name=Perms.OMNIPOTENT)
r.permissions.add(p)
u2.profile.roles.add(r)

# newlines at end to ensure everything runs when piping to the python shell
