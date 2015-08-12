Polymer({
    is: 'vms-tab',

    properties: {
    },

    _vmCreated: function(ev) {
        this.$.list_alive.reload();
    }
});
