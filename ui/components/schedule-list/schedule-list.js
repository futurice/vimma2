Polymer({
    is: 'schedule-list',

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        _url: {
            type: String,
            readOnly: true,
            value: vimmaApiScheduleList
        }
    },
    _scheduleExpanded: function(ev) {
    },
    _scheduleCollapsed: function(ev) {
    }
});
