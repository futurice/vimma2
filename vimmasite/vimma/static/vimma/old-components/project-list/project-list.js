Polymer('project-list', {
    loading: true,
    success: null,
    errorText: null,

    projects: null,

    created: function() {
        var ok = (function(resultsArr) {
            this.loading = false;
            this.success = true;
            this.projects = resultsArr[0];
        }).bind(this);
        var fail = (function(errorText) {
            this.loading = false;
            this.success = false;
            this.errorText = errorText;
        }).bind(this);

        apiGetAll([vimmaApiProjectList], ok, fail);
    },

    click: function(e, detail, sender) {
        e.preventDefault();
        this.fire('project-selected',
                {id: parseInt(sender.getAttribute('prjid'), 10)});
    }
});
