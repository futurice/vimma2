Polymer({
    is: 'schedules-tab',

    _scheduleCreated: function(ev) {
        this.$.list.scheduleCreated(ev.detail);
    }
});
