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
        toggles: {
            type: Boolean,
            computed: 'computeToggles(text, size)',
            observer: 'togglesChanged'
        },
        _collapsed: {
            type: Boolean,
            value: true,
            readOnly: true
        }
    },

    listeners: {
        'track': 'track',
        'tap': 'toggle'
    },

    computeToggles: function(text, size) {
        return text.length > size;
    },
    togglesChanged: function(newV, oldV) {
        this.toggleClass('toggles', newV);
    },

    getText: function(text, size, toggles, collapsed) {
        if (!toggles || !collapsed) {
            return text;
        }
        return text.substr(0, size - 1) + '…';
    },

    // the user ‘dragged’ (selected text): don't toggle, do nothing instead.
    track: function(e) {
    },

    toggle: function() {
        this._set_collapsed(!this._collapsed);
    }
});
