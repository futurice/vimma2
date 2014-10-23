Polymer('audit-display', {
    ajaxInProgress: false,
    ajaxSuccess: true,
    ajaxErrTxt: '',

    onAjaxStart: function(ev) {
        ev.stopPropagation();
        if (this.ajaxInProgress) {
            throw 'ajax-start fired while ajaxInProgress';
        }
        this.ajaxInProgress = true;
    },

    onAjaxEnd: function(ev, detail, sender) {
        ev.stopPropagation();
        if (!this.ajaxInProgress) {
            throw 'ajax-end fired while not ajaxInProgress';
        }
        this.ajaxInProgress = false;
        this.ajaxSuccess = detail.success;
        this.ajaxErrTxt = this.ajaxSuccess ? '' : detail.errorText;
    },

    // currently loading data
    loading: true,
    // the result of the most recent attempt at loading the component's data
    loadingSucceeded: false,

    /* Data model */
    vmid: -1,
    userid: -1,

    pageSize: 5,
    // can't refer to ‘restMaxPaginateBy’ in the template disabled?= binding
    maxPageSize: restMaxPaginateBy,
    // API endpoint response {count:, next:, previous:, results:}
    apiResult: null,
    firstItemNr: 1,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.fire('ajax-start');

        this.loading = true;

        // don't reset the page size
        this.apiResult = null;
        this.firstItemNr = 1;
        this.loadFirstPage();
    },
    loadFail: function(errorText) {
        this.fire('ajax-end', {success: false, errorText: errorText});

        this.loading = false;
        this.loadingSucceeded = false;
    },
    loadSuccess: function() {
        this.fire('ajax-end', {success: true});

        this.loading = false;
        this.loadingSucceeded = true;
    },

    loadFirstPage: function() {
        var url = vimmaApiAuditList;
        var params = [];
        if (this.vmid != -1) {
            params.push('vm=' + this.vmid);
        }
        if (this.userid != -1) {
            params.push('user=' + this.userid);
        }
        params.push(restPaginateByParam + '=' + this.pageSize);
        if (params.length) {
            url += '?' + params.join('&');
        }

        $.ajax({
            url: url,
            success: (function(data) {
                this.apiResult = data;
                this.firstItemNr = this.apiResult.count ? 1 : 0;
                this.loadSuccess();
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.loadFail(errorText);
            }).bind(this)
        });
    },

    loadUrl: function(url, go_right) {
        this.fire('ajax-start');
        var first_right = this.firstItemNr + this.apiResult.results.length;

        $.ajax({
            url: url,
            success: (function(data) {
                this.apiResult = data;

                var first_left = this.firstItemNr - this.apiResult.results.length;
                this.firstItemNr = go_right ? first_right : first_left;

                this.fire('ajax-end', {success: true});
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.fire('ajax-end', {success: false, errorText: errorText});
            }).bind(this)
        });
    },
    loadPrevious: function() {
        this.loadUrl(this.apiResult.previous, false);
    },
    loadNext: function() {
        this.loadUrl(this.apiResult.next, true);
    },

    showMore: function() {
        this.pageSize *= 2;
        this.reload();
    }
});
