Polymer({
    is: 'vms-tab',

    properties: {
      providers: {
        type: Array,
        value: vimmaProviders,
        notify: true
      },
      _vmCreated: {
        type: Boolean,
        value: undefined,
        notify: true
      }
    },

    vmCreated: function(ev) {
        // propagate event form <vm-list>
        this._vmCreated = ev;
    }
});
