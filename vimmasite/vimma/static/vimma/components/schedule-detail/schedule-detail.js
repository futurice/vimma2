Polymer({
    is: 'schedule-detail',

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        scheduleId: {
            type: Number
        },

        /* The url fragment points to this schedule. On transitions to ‘true’,
         * ensure the view is expanded.
         * Triggered on browser (e.g. ‘back/forward/paste url’) navigation
         * but also indirectly after the user expands this component (an event
         * is fired and <schedule-list> changes the URL to point to us).
         */
        selectedViaFrag: {
            type: Boolean,
            observer: '_selectedViaFragChanged'
        },

        _scheduleUrl: {
            type: String,
            computed: '_computeScheduleUrl(scheduleId)'
        },
        _scheduleLoading: Boolean,
        _scheduleError: String,
        _schedule: {
            type: Object,
            observer: '_scheduleChanged'
        },

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
            value: false,
            observer: '_expandedChanged'
        },

        /* User action (delete or save) */
        _actionInFlight: {
            type: Boolean,
            value: false
        },
        _actionError: {
            type: String,
            value: ''
        },

        // Properties for the ‘data model’ we are editing.
        _newName: String,
        _newMatrix: Array,
        _newTzId: Number,
        _newIsSpecial: Boolean,

        _unsavedChanges: {
            type: Boolean,
            computed: '_computeUnsavedChanges(_schedule, _newName, _newMatrix, _newTzId, _newIsSpecial)'
        },
        class: {
            type: String,
            computed: '_getHostClass(_unsavedChanges)',
            reflectToAttribute: true
        }
    },

    _selectedViaFragChanged: function(newV, oldV) {
        if (newV) {
            this._expanded = true;
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

    _expandedChanged: function(newV, oldV) {
        var evName;
        if (newV) {
            evName = 'schedule-expanded';
        } else {
            evName = 'schedule-collapsed';
        }
        this.fire(evName, this.scheduleId);
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

    _save: function(ev) {
        this._actionInFlight = true;
        $.ajax({
            url: vimmaApiScheduleDetailRoot + this.scheduleId + '/',
            type: 'PUT',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                name: this._newName,
                matrix: JSON.stringify(this._newMatrix),
                timezone: this._newTzId,
                is_special: this._newIsSpecial
            }),
            complete: (function() {
                this._actionInFlight = false;
            }).bind(this),
            success: (function(data) {
                this._actionError = '';
                this._schedule = data;
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this._actionError = errorText;
            }).bind(this)
        });
    },

    _toggle: function() {
        this._expanded = !this._expanded;
    },

    _scheduleChanged: function(newV, oldV) {
        this._discardChanges();
    },

    _discardChanges: function() {
        var s = this._schedule;
        this._newName = s.name;
        this._newMatrix = JSON.parse(s.matrix);
        this._newTzId = s.timezone;
        this._newIsSpecial = s.is_special;
    },

    _computeUnsavedChanges: function(schedule,
        newName, newMatrix, newTzId, newIsSpecial) {
        return !sameModels({
            name: schedule.name,
            matrix: JSON.parse(schedule.matrix),
            timezone: schedule.timezone,
            is_special: schedule.is_special
        }, {
            name: newName,
            matrix: newMatrix,
            timezone: newTzId,
            is_special: newIsSpecial
        });
    },

    _newTzSelected: function(ev) {
        this._newTzId = this._timezones[ev.target.selectedIndex].id;
    },

    _getHostClass: function(unsavedChanges) {
        if (unsavedChanges) {
            return 'unsaved';
        }
        return '';
    }
});
