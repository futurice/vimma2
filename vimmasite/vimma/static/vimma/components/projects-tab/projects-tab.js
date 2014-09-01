Polymer('projects-tab', {
    selectedProjectId: null,

    projectSelected: function(e, detail, sender) {
        e.stopPropagation();
        this.selectedProjectId = e.detail.id;
    },
    unselectProject: function() {
        this.selectedProjectId = null;
    }
});
