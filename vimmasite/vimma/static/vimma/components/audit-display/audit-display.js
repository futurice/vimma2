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
    // {userId: userObject, …}
    usersById: null,
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
        this.usersById = null;
        this.apiResult = null;
        this.firstItemNr = 1;
        this.loadUsers();
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

    loadUsers: function() {
        var ok = (function(arr) {
            var byId = {};
            arr[0].forEach(function(u) {
                byId[u.id] = u;
            });
            this.usersById = byId;

            this.loadFirstPage();
        }).bind(this);
        apiGetAll([vimmaApiUserList], ok, this.loadFail.bind(this));
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

        var ok = (function(arr) {
            this.apiResult = arr[0];
            this.firstItemNr = this.apiResult.count ? 1 : 0;
            this.loadSuccess();
        }).bind(this);
        apiGet([url], ok, this.loadFail.bind(this));
    },

    loadUrl: function(url, go_right) {
        this.fire('ajax-start');
        var first_right = this.firstItemNr + this.apiResult.results.length;

        var ok = (function(arr) {
            this.apiResult = arr[0];

            var first_left = this.firstItemNr - this.apiResult.results.length;
            this.firstItemNr = go_right ? first_right : first_left;

            this.fire('ajax-end', {success: true});
        }).bind(this);
        var fail = (function(errorText) {
            this.fire('ajax-end', {success: false, errorText: errorText});
        }).bind(this);

        apiGet([url], ok, fail);
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
    },

    getUserText: function(userId) {
        if (userId == null) {
            return '—';
        }
        if (!(userId in this.usersById)) {
            return userId + '?';
        }
        return this.usersById[userId].username;
    }
});
