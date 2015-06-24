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
        _timezones: Array
    },

    _toggle: function() {
        this._expanded = !this._expanded;
    }
});
