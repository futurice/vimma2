Polymer({
    is: 'schedule-detail',
    
    ready: function() {
      this.$.form._requestBot.headers = {'X-CSRFToken': $.cookie('csrftoken')};
    },

    csrfTokenHeader: function() {
      return JSON.stringify({'X-CSRFToken': $.cookie('csrftoken')});
    },

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        scheduleId: {
            type: Number
        },

        _schedule: {
            type: Object
        },

        schedule: {
            type: Object,
            notify: true
        },

        _scheduleUrl: {
            type: String,
            computed: '_computeScheduleUrl(scheduleId)'
        },

        _tzUrl: {
            type: String,
            readOnly: true,
            value: vimmaApiTimeZoneList
        },

        _error: {
            type: String
        },

        _unsavedChanges: {
            type: Boolean,
            computed: '_computeUnsavedChanges(schedule.*)'
        },
        class: {
            type: String,
            computed: '_getHostClass(_unsavedChanges)',
            reflectToAttribute: true
        }
    },
    observers: [
      '_scheduleChanged(schedule)'
    ],

    parse: function(value) {
      return JSON.parse(value);
    },

    _computeScheduleUrl: function(scheduleId) {
        return vimmaApiScheduleDetailRoot + scheduleId + '/';
    },

    _tzName: function(tzArray, tzId) {
        var n = tzArray.length, i, crt;
        for (i = 0; i < n; i++) {
            crt = tzArray[i];
            if (crt.id == tzId) {
                return crt.name;
            }
        }
    },

    _delete: function(ev) {
        if (!confirm('Delete Schedule: ‘'+this.schedule.name+'’?')) {
            return;
        }
        this.$.deleteButtonAjax.generateRequest();
    },

    submitForm: function() {
      f = document.getElementById('form');
      f.submit();
        // TODO: form-errors
    },

    toggle: function() {
        this.$.collapse.toggle();
    },

    _scheduleChanged: function(schedule) {
      this._schedule = clone(this.schedule);
    },

    _discardChanges: function() {
      this.schedule = this._schedule;
    },

    _computeUnsavedChanges: function(schedule) {
        if(!this._schedule) {
          // TODO: _schedule should be available at this point
          return false;
        }
        if(schedule.base && schedule.value) {
          // computed:.* changes propagate as {base:,value:,?:}
          schedule = schedule.value;
        }
        return !sameModels(schedule, this._schedule);
    },

    timezoneSelected: function(ev) {
        this.set('schedule.timezone', this.timezones.results[ev.target.selectedIndex]['id']);
    },

    _getHostClass: function(unsavedChanges) {
        if (unsavedChanges) {
            return 'unsaved';
        }
        return '';
    }
});
