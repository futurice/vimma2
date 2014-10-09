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

    // How many items to show at first
    initialCount: 5,

    created: function() {
        this.allAuditItems = [];
        this.shownAuditItems = [];
    },

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.fire('ajax-start');

        this.loading = true;

        this.allAuditItems = [];

        this.loadAudits();
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

    loadAudits: function() {
        var ok = (function(resultArr) {
            this.allAuditItems = resultArr[0];
            this.loadSuccess();
        }).bind(this);

        var url = vimmaApiAuditList;
        var params = [];
        if (this.vmid != -1) {
            params.push('vm=' + this.vmid);
        }
        if (this.userid != -1) {
            params.push('user=' + this.userid);
        }
        if (params.length) {
            url += '?' + params.join('&');
        }

        apiGetAll([url], ok, this.loadFail.bind(this));
    },

    allAuditItemsChanged: function() {
        this.shownAuditItems = this.allAuditItems.slice(0, this.initialCount);
    },

    showMore: function() {
        this.shownAuditItems = this.allAuditItems.slice(0,
                this.shownAuditItems.length * 2);
    }
});
