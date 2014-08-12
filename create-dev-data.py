from vimma.util import createUser
from vimma.models import Schedule
import json

createUser('u1', 'u1@example.com', 'pass')
Schedule.objects.create(matrix=json.dumps(
    7*[10*2*[False] + 8*2*[True] + 6*2*[False]])).full_clean()
