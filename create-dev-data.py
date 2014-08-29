from vimma.util import create_vimma_user
from vimma.models import TimeZone, Schedule, Role, Permission, Project
from vimma.perms import Perms
import json

u1 = create_vimma_user('u1', 'u1@example.com', 'pass')
tz_hki = TimeZone.objects.create(name='Europe/Helsinki')
TimeZone.objects.create(name='Europe/London')
TimeZone.objects.create(name='America/Los_Angeles')
Schedule.objects.create(name='My Schedule', timezone=tz_hki,
        matrix=json.dumps(7*[10*2*[False] + 8*2*[True] + 6*2*[False]])
        ).full_clean()

u2 = create_vimma_user('u2', 'u2@example.com', 'pass')
r = Role.objects.create(name='omnipotent')
p = Permission.objects.create(name=Perms.OMNIPOTENT)
r.permissions.add(p)
u2.profile.roles.add(r)

prj1 = Project.objects.create(name='A Project', email='prj1@example.com')
u1.profile.projects.add(prj1)

prj2 = Project.objects.create(name='Second Project', email='prj2@example.com')
u2.profile.projects.add(prj2)

# newlines at end to ensure everything runs when piping to the python shell
