Polymer({
    is: 'vms-tab',

    properties: {
        frag: {
            type: String,
            notify: true
        }
    },

    _vmCreated: function(ev) {
        this.$.list_alive.reload();
    }
});
