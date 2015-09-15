
class Perms:
    OMNIPOTENT = 'omnipotent'
    # Create, delete, edit schedules
    EDIT_SCHEDULE = 'schedule-edit'
    USE_SPECIAL_SCHEDULE = 'schedule-use-special'
    # see projects you're not a member of
    READ_ANY_PROJECT = 'read-any-project'
    # create VMs from a Config belonging to a ‘special’ Provider
    USE_SPECIAL_PROVIDER = 'provider-use-special'
    # create VMs from a Config which needs this additional permission
    USE_SPECIAL_VM_CONFIG = 'vm-config-use-special'
    # read all audits
    READ_ALL_AUDITS = 'read-all-audits'
    READ_ALL_POWER_LOGS = 'read-all-power-logs'

# Collect all permissions so we can pre-populate the DB with them
ALL_PERMS = {getattr(Perms, x) for x in dir(Perms) if not x.startswith('_')}
