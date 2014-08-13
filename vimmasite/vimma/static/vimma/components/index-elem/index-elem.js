Polymer('index-elem', {
    selectedId: null,
    tabIds: {
        SCHEDULES: 'schedules',
        ANOTHER: 'another-tab',
        THIRD: 'third-tab'
    },
    onCoreSelect: function(e, detail, sender) {
        if (detail.isSelected) {
            this.selectedId = detail.item.getAttribute('id');
        }
    }
});
