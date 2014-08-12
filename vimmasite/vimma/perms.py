"""
List all permissions.
"""

# DRY Principle: define all permissions, so we can refer to them later, and
# make a list with all permissions, simultaneously.

class Perms:
    """
    Define symbolic names so we can refer to Permissions as Perms.MY_PERM.
    """
    OMNIPOTENT = 'omnipotent'
    # Create, delete, edit schedules
    EDIT_SCHEDULE = 'schedule-edit'
    USE_SPECIAL_SCHEDULE = 'schedule-use-special'

# Collect all permissions so we can pre-populate the DB with them
ALL_PERMS = {x:getattr(Perms, x) for x in dir(Perms) if not x.startswith('_')}
