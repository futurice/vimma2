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
    # see projects you're not a member of
    READ_ANY_PROJECT = 'read-any-project'
    # create VMs from a VMConfig which needs this additional permission
    USE_SPECIAL_VM_CONFIG = 'vm-config-use-special'
    # read all audits
    READ_ALL_AUDITS = 'read-all-audits'

# Collect all permissions so we can pre-populate the DB with them
ALL_PERMS = {getattr(Perms, x) for x in dir(Perms) if not x.startswith('_')}
