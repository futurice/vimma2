Polymer({
    is: 'expiration-item',

    properties: {
        vm: {
            type: Number,
            observer: 'vmChanged'
        },

        noExplanation: {
            type: Boolean,
            value: false
        },

        _loadingToken: Object,  // same logic as in <vm-list>
        _loading: Boolean,
        _loadErr: String,   // empty string if no error
        _actionInFlight: Boolean,
        _actionErr: String,

        _exp: Object,
        _dateStr: String,
        _timeStr: String
    },

    vmChanged: function(newV, oldV) {
        this._reload();
    },

    _reload: function() {
    },

    _openDialog: function() {
        function zeroPref(n) {
            if (n < 10) {
                return '0' + n;
            }
            return n + '';
        }
        var exp = new Date(this._exp.expires_at);
        this._dateStr = exp.getFullYear() + '-' +
            zeroPref(exp.getMonth() + 1) + '-' + zeroPref(exp.getDate());
        this._timeStr = zeroPref(exp.getHours()) + ':' +
            zeroPref(exp.getMinutes());

        this.$.dialog.open();
    },
    _dialogClosed: function() {
        if (!this.$.dialog.closingReason.confirmed) {
            return;
        }

        var year, month, day, hour, minute;
        var parts = this._dateStr.split('-');
        year = parseInt(parts[0], 10);
        month = parseInt(parts[1], 10);
        day = parseInt(parts[2], 10);
        parts = this._timeStr.split(':');
        hour = parseInt(parts[0], 10);
        minute = parseInt(parts[1], 10);

        var exp = new Date(year, month-1, day, hour, minute);
        var timestamp = Math.floor(exp.valueOf() / 1000)
        // TODO: submit expiration
    },
    _setExpiryClass: function() {
        var d = new Date(this._exp.expires_at).valueOf(),
            now = new Date().valueOf(),
            soon = d - now < 1000*60*60*24*30;
        if (d < now) {
            this.classList.add('expires-expired');
        } else if (soon) {
            this.classList.add('expires-soon');
        } else {
            this.classList.remove('expires-soon');
            this.classList.remove('expires-expired');
        }
    },
});
