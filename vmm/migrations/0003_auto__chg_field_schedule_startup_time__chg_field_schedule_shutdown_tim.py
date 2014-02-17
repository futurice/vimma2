# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Schedule.startup_time'
        db.alter_column(u'vmm_schedule', 'startup_time', self.gf('django.db.models.fields.TimeField')(null=True))

        # Changing field 'Schedule.shutdown_time'
        db.alter_column(u'vmm_schedule', 'shutdown_time', self.gf('django.db.models.fields.TimeField')(null=True))

        # Changing field 'VirtualMachine.instance_id'
        db.alter_column(u'vmm_virtualmachine', 'instance_id', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'VirtualMachine.comment'
        db.alter_column(u'vmm_virtualmachine', 'comment', self.gf('django.db.models.fields.CharField')(max_length=1024, null=True))

        # Changing field 'VirtualMachine.persist_until'
        db.alter_column(u'vmm_virtualmachine', 'persist_until', self.gf('django.db.models.fields.DateTimeField')(null=True))

    def backwards(self, orm):

        # Changing field 'Schedule.startup_time'
        db.alter_column(u'vmm_schedule', 'startup_time', self.gf('django.db.models.fields.TimeField')(default=None))

        # Changing field 'Schedule.shutdown_time'
        db.alter_column(u'vmm_schedule', 'shutdown_time', self.gf('django.db.models.fields.TimeField')(default=None))

        # Changing field 'VirtualMachine.instance_id'
        db.alter_column(u'vmm_virtualmachine', 'instance_id', self.gf('django.db.models.fields.CharField')(default=None, max_length=64))

        # Changing field 'VirtualMachine.comment'
        db.alter_column(u'vmm_virtualmachine', 'comment', self.gf('django.db.models.fields.CharField')(default=None, max_length=1024))

        # Changing field 'VirtualMachine.persist_until'
        db.alter_column(u'vmm_virtualmachine', 'persist_until', self.gf('django.db.models.fields.DateTimeField')(default=None))

    models = {
        u'vmm.schedule': {
            'Meta': {'object_name': 'Schedule'},
            'days_up': ('django.db.models.fields.CharField', [], {'default': "'tttttff'", 'max_length': '7'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'shutdown_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'}),
            'startup_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'vmm.virtualmachine': {
            'Meta': {'object_name': 'VirtualMachine'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'persist_until': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'primary_name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'schedule': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vmm.Schedule']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'undefined'", 'max_length': '32'}),
            'updated_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['vmm']