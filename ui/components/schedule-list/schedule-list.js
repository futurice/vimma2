Polymer({
    is: 'schedule-list',

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        url: {
            type: String,
            value: url('schedule-list')
        }
    },
    _scheduleExpanded: function(ev) {
    },
    _scheduleCollapsed: function(ev) {
    },
    _scheduleDeleted: function(ev) {
    }
});
