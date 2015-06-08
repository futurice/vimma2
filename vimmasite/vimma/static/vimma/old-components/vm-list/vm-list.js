Polymer('vm-list', {
    frag: '',

    created: function() {
        this.vmids = [];
    },

    vmExpanded: function(ev, detail, sender) {
        ev.stopPropagation();
        this.frag = '' + ev.target.templateInstance.model.vmid;
    },

    vmCollapsed: function(ev, detail, sender) {
        ev.stopPropagation();
        this.frag = '';
    }
});
