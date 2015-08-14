Polymer({
    is: 'override-schedule',

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        vm: {
            type: Object,
            observer: '_vmidChanged'
        },

        _loadingToken: Object,  // same logic as in <vm-list>
        _loading: Boolean,
        _loadErr: String,
        _vm: Object,

        _actionInFlight: Boolean,
        _actionErr: String,

        _showNewOverride: {
            type: Boolean,
            value: false
        },
        _newOverride: {
            type: Boolean,
            value: true
        },
        _durationMins: {
            type: String,
            value: '60'
        }
    },

    _vmidChanged: function(newV, oldV) {
    },

    _reload: function() {
    },

    _toggleNewOverride: function() {
        this._showNewOverride = !this._showNewOverride;
    },

    _getNewOverrideLabel: function(newOverride) {
        if (newOverride) {
            return 'Powered ON';
        }
        return 'Powered OFF';
    },

    _setNewOverride: function() {
        this._performAction({
            vmid: this.vmid,
            state: this._newOverride,
            seconds: Math.floor(parseInt(this._durationMins, 10) * 60)
        });
    },

    _clearOverride: function() {
        this._performAction({
            vmid: this.vmid,
            state: null
        });
    },

    _performAction: function(jsonBody) {
        var token = this._loadingToken;
        this._actionInFlight = true;
        $.ajax({
            url: vimmaEndpointOverrideSchedule,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify(jsonBody),
            success: (function(data) {
                if (this._loadingToken != token) {
                    return;
                }

                this._reload();
            }).bind(this),
            error: (function() {
                if (this._loadingToken != token) {
                    return;
                }

                var errorText = getAjaxErr.apply(this, arguments);
                this._actionErr = errorText;
                this._actionInFlight = false;
            }).bind(this)
        });
    },

    _secs2millis: function(epochSecs) {
        return epochSecs * 1000;
    }
});
