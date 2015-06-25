Polymer({
    is: 'schedule-detail',

    properties: {
        scheduleId: {
            type: Number
        },

        _scheduleUrl: {
            type: String,
            computed: '_computeScheduleUrl(scheduleId)'
        },
        _scheduleLoading: Boolean,
        _scheduleError: String,
        _schedule: Object,

        _tzUrl: {
            type: String,
            readOnly: true,
            value: vimmaApiTimeZoneList
        },
        _tzLoading: Boolean,
        _tzError: String,
        _timezones: Array,

        _loading: {
            type: Boolean,
            computed: '_computeLoading(_scheduleLoading, _tzLoading)'
        },
        _error: {
            type: String,
            computed: '_computeError(_scheduleError, _tzError)'
        },

        _expanded: {
            type: Boolean,
            value: false
        },

        /* User action (delete or save) */
        _actionInFlight: {
            type: Boolean,
            value: false
        },
        _actionError: {
            type: String,
            value: ''
        }
    },

    _computeScheduleUrl: function(scheduleId) {
        return vimmaApiScheduleDetailRoot + scheduleId + '/';
    },

    _computeLoading: function() {
        var i, n = arguments.length, crt;
        for (i = 0; i < n; i++) {
            crt = arguments[i];
            if (crt) {
                return true;
            }
        }
        return false;
    },
    _computeError: function() {
        var i, n = arguments.length, crt;
        for (i = 0; i < n; i++) {
            crt = arguments[i];
            if (crt) {
                return crt;
            }
        }
        return '';
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
        ev.stopPropagation();
        if (!confirm('Delete Schedule: ‘' + this._schedule.name + '’?')) {
            return;
        }

        this._actionInFlight = true;
        $.ajax({
            url: vimmaApiScheduleDetailRoot + this.scheduleId + '/',
            type: 'DELETE',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            complete: (function() {
                this._actionInFlight = false;
            }).bind(this),
            success: (function(data) {
                this._actionError = '';
                this.fire('schedule-deleted', this.scheduleId);
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this._actionError = errorText;
            }).bind(this)
        });
    },
    _toggle: function() {
        this._expanded = !this._expanded;
    }
});
