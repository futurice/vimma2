Polymer('index-elem', {
    selectedId: null,
    tabIds: {
        SCHEDULES: 'schedules',
        PROJECTS: 'projects',
        THIRD: 'third-tab'
    },
    onCoreSelect: function(e, detail, sender) {
        if (detail.isSelected) {
            this.selectedId = detail.item.getAttribute('id');
        }
    }
});
