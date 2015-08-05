Polymer({
    is: 'schedules-tab',

    properties: {
    },

    _scheduleCreated: function(ev) {
        this.$.list.scheduleCreated(ev.detail);
    }
});
