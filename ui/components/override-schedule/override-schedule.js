Polymer({
    is: 'override-schedule',

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        vm: {
            type: Object,
            observer: '_vmidChanged'
        },

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
        // TODO: vimmaEndpointOverrideSchedule override-schedule
    },

    _secs2millis: function(epochSecs) {
        return epochSecs * 1000;
    }
});
