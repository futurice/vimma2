Polymer({
    is: 'create-vm-aws-data',

    properties: {
        data: {
            type: Object,
            readOnly: true,
            notify: true
        }
    },
    // See ‘create-vm-dummy-data’ for why ‘ready’ instead of ‘default value’.
    ready: function() {
        this._setData({
            name: ''
        });
    }
});
