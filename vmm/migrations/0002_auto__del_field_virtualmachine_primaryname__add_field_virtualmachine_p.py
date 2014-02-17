# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'VirtualMachine.primaryname'
        db.delete_column(u'vmm_virtualmachine', 'primaryname')

        # Adding field 'VirtualMachine.primary_name'
        db.add_column(u'vmm_virtualmachine', 'primary_name',
                      self.gf('django.db.models.fields.CharField')(default=None, max_length=256),
                      keep_default=False)


    def backwards(self, orm):
        # Adding field 'VirtualMachine.primaryname'
        db.add_column(u'vmm_virtualmachine', 'primaryname',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=256),
                      keep_default=False)

        # Deleting field 'VirtualMachine.primary_name'
        db.delete_column(u'vmm_virtualmachine', 'primary_name')


    models = {
        u'vmm.schedule': {
            'Meta': {'object_name': 'Schedule'},
            'days_up': ('django.db.models.fields.CharField', [], {'default': "'tttttff'", 'max_length': '7'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'shutdown_time': ('django.db.models.fields.TimeField', [], {'blank': 'True'}),
            'startup_time': ('django.db.models.fields.TimeField', [], {'blank': 'True'})
        },
        u'vmm.virtualmachine': {
            'Meta': {'object_name': 'VirtualMachine'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance_id': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'persist_until': ('django.db.models.fields.DateTimeField', [], {}),
            'primary_name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'schedule': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['vmm.Schedule']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'undefined'", 'max_length': '32'}),
            'updated_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['vmm']