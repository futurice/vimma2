from django.utils.timezone import utc

import datetime

from vimma.audit import Auditor
from vimma.util import schedule_at_tstamp
from vimma.celery import app

aud = Auditor(__name__)

class VMController():
    """
    Base class showing common VM operations.
    """

    def __init__(self, vm):
        self.vm = vm

    def power_on(self, user_id=None):
        raise NotImplementedError()

    def power_off(self, user_id=None):
        raise NotImplementedError()

    def reboot(self, user_id=None):
        raise NotImplementedError()

    def destroy(self, user_id=None):
        raise NotImplementedError()

    def update_status(self):
        """
        This method is responsible for the following actions (e.g. schedule
        them as asynchronous tasks):
        Get the VM status from the remote provider, save it in the Vimma DB and
        mark the timestamp of this update.
        Call power_log() to log the current power state (on or off).
        Call switch_on_off() which turns the vm on or off if needed.
        """
        raise NotImplementedError()

    def can_change_firewall_rules(self, user):
        return can_do(user, Actions.CREATE_VM_IN_PROJECT, self.vm.project)

    def create_firewall_rule(self, data, user_id=None):
        """
        Create a firewall rule with data specific to the vm type.
        """
        raise NotImplementedError()

    def delete_firewall_rule(self, fw_rule_id, user_id=None):
        raise NotImplementedError()

    def power_log(self, powered_on):
        """
        PowerLog the current vm state (ON/OFF).
        """
        raise NotImplementedError()

    def set_vm_status_updated_at_now(self):
        self.vm._meta.model.objects.filter(id=self.vm.pk).update(status_updated_at=datetime.datetime.utcnow().replace(tzinfo=utc))

    def switch_on_off(self, powered_on):
        """
        Power on/off the vm if needed.

        powered_on must be a boolean showing the current vm state.
        If the vm's power state should be different, a power_on or power_off task
        is submitted.
        """
        with aud.ctx_mgr(vm_id=self.vm.pk):
            if type(powered_on) is not bool:
                raise ValueError('powered_on ‘{}’ has type ‘{}’, want ‘{}’'.format(
                    powered_on, type(powered_on), bool))

            # TODO: maybe move this to the update status task
            # clean-up, but not required
            self.discard_expired_schedule_override()

            new_power_state = self.vm_at_now()
            if powered_on is new_power_state:
                return

            if new_power_state:
                self.power_on()
            else:
                self.power_off()


    def discard_expired_schedule_override(self):
        """
        Remove schedule override, if it has expired, from vm_id.

        This function must not be called inside a transaction.
        """
        """
        Returns True if an expired override was discarded, else False.
        """
        now = datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()
        aud.debug('Discarded expired schedule override', vm_id=self.vm.pk)

        if self.vm.sched_override_state == None:
            return False
        if self.vm.sched_override_tstamp >= now:
            return False

        self.vm.sched_override_state = None
        self.vm.sched_override_tstamp = None
        self.vm.save()
        return True

    def vm_at_now(self):
        """
        Return True/False if vm should be powered ON/OFF now.

        If the VM has expired → OFF. Else if there's a schedule override, use that.
        Else computed from the vm's schedule.
        """
        if not self.vm.expiration:
            return False

        now = datetime.datetime.utcnow().replace(tzinfo=utc).timestamp()
        if now > self.vm.expiration.expires_at.timestamp():
            return False
        if (vm.sched_override_state != None and
                self.vm.sched_override_tstamp >= now):
            return self.vm.sched_override_state
        return schedule_at_tstamp(self.vm.schedule, now)

    @app.task
    def expiration_notify(self):
        aud.warning('Notify of VM expiration on ' + str(exp_date),
                vm_id=self.vm.pk)
        return self.vm.expiration.expires_at


    def create_vm_details(self, data, user_id, *args, **kwargs):
        raise NotImplementedError()

    def create_vm(self, config, project, schedule, comment, user_id):
        """
        Create a new VM, return its ID if successful otherwise throw an exception.

        The user is only needed to record in an audit message. Permission checking
        has already been done elsewhere.
        The data arg is specific to the provider type.
        This function must not be called inside a transaction.
        """
        aud.debug(('Request to create VM: ' +
            'config {config.id} ({config.name}), ' +
            'project {project.id} ({project.name}’), ' +
            'schedule {schedule.id} ({schedule.name}), ' +
            'comment ‘{comment}’, data ‘{data}’').format(
                config=config, project=project, schedule=schedule,
                comment=comment, data=data),
            user_id=user_id)

        callables = []
        # database
        with transaction.atomic():
            prov = config.provider
            user = User.objects.get(id=user_id)
            now = datetime.datetime.utcnow().replace(tzinfo=utc)
            sched_override_tstamp = (now.timestamp() +
                    settings.VM_CREATION_OVERRIDE_SECS)

            expire_dt = now + datetime.timedelta(seconds=settings.DEFAULT_VM_EXPIRY_SECS)

            vmexp = VMExpiration.objects.create(expires_at=expire_dt)

            vm, callables = self.create_vm_details(data=data, user_id=user_id, config=config)
            aud.info('Created VM', user_id=user_id, vm_id=vm.id)
        # background tasks
        for c in callables:
            c()
        return vm_id

