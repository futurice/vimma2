from django.core.management.base import BaseCommand, CommandError

from vimma.models import Permission
from vimma.perms import ALL_PERMS


class Command(BaseCommand):
    args = ''
    help = 'Creates all missing Vimma Permissions'

    def handle(self, *args, **options):
        for name in ALL_PERMS:
            p,_ = Permission.objects.get_or_create(name=name)
