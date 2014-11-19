Polymer('vm-recent-errors', {
    vmid: 0,
    maxsecs: 60*60*24,
    // if there are no errors, say it (instead of being silent)
    showabsence: false,

    loading: true,
    loadingSucceeded: false,

    pageSize: 10,
    nowSecs: 0,
    errors: 0,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');

        this.loading = true;

        this.nowSecs = Math.round(new Date().valueOf() / 1000);
        this.errors = 0;

        this.loadAudits();
    },
    loadFail: function(errorText) {
        this.$.ajax.fire('end', {success: false, errorText: errorText});

        this.loading = false;
        this.loadingSucceeded = false;
    },
    loadSuccess: function() {
        this.$.ajax.fire('end', {success: true});

        this.loading = false;
        this.loadingSucceeded = true;
    },

    loadAudits: function() {
        var url = (function getUrl() {
            var url = vimmaApiAuditList;
            var params = [];
            params.push('min_level=' +
                    encodeURIComponent(auditLevels[auditLevels.length-1].id));
            params.push('vm=' + encodeURIComponent(this.vmid));
            params.push(restPaginateByParam + '=' + this.pageSize);
            if (params.length) {
                url += '?' + params.join('&');
            }
            return url;
        }).bind(this)();

        var ok = (function(resultArr) {
            // O(N) linear search is faster to write than O(log N) binary
            // search and should suffice for the current short array.
            var audits = resultArr[0].results;
            var i, crtSecs;
            for (i = 0; i < audits.length; i++) {
                crtSecs = Math.round(
                        new Date(audits[i].timestamp).valueOf() / 1000);
                if (this.nowSecs - crtSecs > this.maxsecs) {
                    break;
                }
            }
            // i is the first one older than maxsecs, or audits.length
            this.errors = i;
            this.loadSuccess();
        }).bind(this);

        apiGet([url], ok, this.loadFail.bind(this));
    }
});
