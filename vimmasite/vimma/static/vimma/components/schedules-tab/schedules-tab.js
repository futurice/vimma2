Polymer({
    is: 'schedules-tab',

    properties: {
        frag: {
            type: String,
            notify: true
        }
    },

    _scheduleCreated: function(ev) {
        this.$.list.scheduleCreated(ev.detail);
    }
});
