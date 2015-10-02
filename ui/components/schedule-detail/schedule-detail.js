Polymer({
    is: 'schedule-detail',

    csrfTokenHeader: function() {
      return JSON.stringify({'X-CSRFToken': $.cookie('csrftoken')});
    },

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        scheduleId: {
            type: Number
        },

        schedule: {
            type: Object,
            notify: true
        },

        scheduleDetailUrl: {
            type: String,
            computed: '_computeScheduleUrl(scheduleId)'
        },

        tzUrl: {
            type: String,
            readOnly: true,
            value: url('timezone-list')
        },

        _error: {
            type: String
        }

    },
    observers: [
    ],

    parse: function(value) {
      return JSON.parse(value);
    },

    coerce: function(val) {
      return !!val;
    },

    _computeScheduleUrl: function(scheduleId) {
        return url('schedule-detail', [scheduleId]);
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
        this.fire('schedule-deleted', {schedule: this.schedule})
    },

    submitForm: function() {
      f = document.getElementById('schedule-form');
      f._requestBot.headers = {
        'X-CSRFToken': $.cookie('csrftoken'),
        'X-HTTP-Method-Override': 'PATCH'};
      f.submit();
      // TODO: form-errors
    },

    toggle: function() {
        this.$.collapse.toggle();
    },

    timezoneSelected: function(ev) {
        this.set('schedule.timezone', this.timezones.results[ev.target.selectedIndex]['id']);
    }
});
