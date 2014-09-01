Polymer('project-detail', {
    prjid: null,
    model: null,
    loading: true,
    success: null,
    errorText: null,

    ready: function() {
        var ok = (function(resultArr) {
            this.loading = false;
            this.success = true;
            this.model = resultArr[0];
        }).bind(this),
        fail = (function(errorText) {
            this.loading = false;
            this.success = false;
            this.errorText = errorText;
        }).bind(this);
        apiGet([vimmaApiProjectDetailRoot + this.prjid + '/'], ok, fail);
    }
});
