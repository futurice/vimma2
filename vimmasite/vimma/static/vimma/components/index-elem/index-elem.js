Polymer('index-elem', {
    selectedId: null,
    tabIds: {
        SCHEDULES: 'schedules',
        PROJECTS: 'projects',
        VMS: 'vms'
    },
    onCoreSelect: function(e, detail, sender) {
        if (detail.isSelected) {
            this.selectedId = detail.item.getAttribute('id');
        }
    }
});
