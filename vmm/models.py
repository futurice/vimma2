from django.db import models

# Create your models here.

class Schedule(models.Model):
    """ A startup / shutdown schdule model """
    # Name of the schedule
    description = models.CharField(max_length=128)
    # Daily startup and shutdown times 
    startup_time = models.TimeField(u"Instance Startup Time", blank=True, null=True)
    shutdown_time = models.TimeField(u"Instance Shutdown Time", blank=True, null=True)
    # Days on. week starts on Monday (t = On, f = Off)
    days_up = models.CharField(max_length=7, default=5 * 't' + 'ff')
    
    def __unicode__(self):
        return self.description
    
    def is_active(self):
        """ Return true if schedule allows VM to be on, otherwise false. """
        # TBD: implement
        return True


class VirtualMachine(models.Model):
    """ Model of an AWS instance """
    # primary_name, Primary DNS name of the server eg. exempli.dev.futuhosting.com
    primary_name = models.CharField(max_length=256)
    # creation_date, Creation date of the instance
    creation_date = models.DateTimeField(u"Instance creation time", auto_now_add=True)
    # Instance name, AWS instance ID
    instance_id = models.CharField(max_length=64, blank=True, null=True)

    # Last updated
    updated_date = models.DateTimeField(u"Instance update time", auto_now=True)
    # Instance status, our internal status (creating, running, shutdown, undefined etc)
    status = models.CharField(max_length=32, default='undefined')
    # General comment field
    comment = models.CharField(u"Optional comments regarding the instance", max_length=1024, blank=True, null=True)
    # Startup and shutdown schedule of the instance
    schedule = models.ForeignKey(Schedule)
    # Override the schedule. The instance will not be automatically shut down before this point in time.
    persist_until = models.DateTimeField(u"Persist the instance until this date", blank=True, null=True)
    
    def __unicode__(self):
        return self.primary_name

    
