Polymer({
    is: 'create-schedule',

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        _expanded: {
            type: Boolean,
            value: false
        },

        _tzApiUrl: {
            type: String,
            readOnly: true,
            value: vimmaApiTimeZoneList
        },
        _loading: Boolean,
        _loadErr: String,
        _timezones: {
            type: Array,
            observer: '_timezonesChanged'
        },

        _newName: String,
        _newTz: Object,

        _createInFlight: {
            type: Boolean,
            value: false
        },
        _createError: {
            type: String,
            value: ''
        }
    },

    _toggle: function() {
        this._expanded = !this._expanded;
        if (this._expanded) {
            this._newName = '';
        }
    },

    _timezonesChanged: function(newV, oldV) {
        if (newV.length) {
            this._newTz = newV[0];
        } else {
            this._newTz = null;
        }
    },

    _newTzSelected: function(ev) {
        this._newTz = this._timezones[ev.target.selectedIndex];
    },

    _create: function() {
        this._createInFlight = true;

        var matrix = [];
        var i, j, row;
        for (i = 0; i < 7; i++) {
            row = [];
            for (j = 0; j < 48; j++) {
                row.push(false);
            }
            matrix.push(row);
        }

        $.ajax({
            url: vimmaApiScheduleList,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                name: this._newName,
                timezone: this._newTz.id,
                matrix: JSON.stringify(matrix)
            }),
            complete: (function() {
                this._createInFlight = false;
            }).bind(this),
            success: (function(data) {
                this._createError = '';
                this._toggle();
                this.fire('schedule-created', data.id);
            }).bind(this),
            error: (function(xhr, txtStatus, saveErr) {
                var errorText = getAjaxErr.apply(this, arguments);
                this._createError = errorText;
            }).bind(this)
        });
    }
});
