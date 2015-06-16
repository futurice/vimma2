Polymer({
    is: 'plain-text',

    properties: {
        text: {
            type: String,
            value: ''
        },
        size: {
            type: Number,
            value: 30
        },
        _collapse: {
            type: Boolean,
            value: true,
            readOnly: true
        }
    },

    listeners: {
        'track': 'track',
        'tap': 'toggle'
    },

    getText: function(text, size, collapse) {
        if (size < 1) {
            size = 1;
        }
        if (!collapse || text.length <= size) {
            return text;
        }
        return text.substr(0, size - 1) + '…';
    },

    // the user ‘dragged’ (selected text): don't toggle, do nothing instead.
    track: function(e) {
    },

    toggle: function() {
        this._set_collapse(!this._collapse);
    }
});
