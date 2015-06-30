Polymer({
    is: 'create-vm-dummy-data',

    properties: {
        data: {
            type: Object,
            readOnly: true,
            notify: true
        }
    },
    /* Default property values don't notify the parent on creation, so setting
     * ‘data’ at the ‘ready’ stage.
     */
    ready: function() {
        this._setData({
            name: '',
            delay: 15
        });
    },

    observers: [
        '_parseDelay(data.delay)'
    ],

    _parseDelay: function(delay) {
        if (typeof(delay) === 'number') {
            return;
        }
        this.set('data.delay', parseInt(delay, 10));
    }
});
