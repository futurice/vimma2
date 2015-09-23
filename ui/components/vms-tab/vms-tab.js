Polymer({
    is: 'vms-tab',

    properties: {
      providers: {
        type: Array,
        value: vimmaProviders,
      }
    },

    _vmCreated: function(ev) {
        this.$.list_alive.reload();
    }
});
