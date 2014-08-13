from vimma.util import create_vimma_user
from vimma.models import Schedule
import json

create_vimma_user('u1', 'u1@example.com', 'pass')
Schedule.objects.create(name='My Schedule',
        matrix=json.dumps(7*[10*2*[False] + 8*2*[True] + 6*2*[False]])
        ).full_clean()
