(function() {
    // Direction followed when loading a new Audit page.
    var DIRECTION = {
        START: 'start',
        LEFT: 'left',
        RIGHT: 'right'
    };

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

        /* Data model */
        vmid: -1,
        userid: -1,
        auditLevels: auditLevels,
        minLevelIdx: 1,

        // API endpoint response {count:, next:, previous:, results:}
        apiResult: null,
        firstItemNr: 1,
        // {userId: userObject, …}
        usersById: null,

        // While loading data: future: {apiResult:…, firstItemNr:…, usersById:…}.
        // When done, assign the new data to the top level fields.
        future: null,

        pageSize: 5,
        // can't refer to ‘restMaxPaginateBy’ in the template disabled?= binding
        maxPageSize: restMaxPaginateBy,

        ready: function() {
            this.reload();
        },

        reload: function() {
            this.fire('ajax-start');

            this.apiResult = null;
            this.firstItemNr = 1;
            this.usersById = null;
            // don't reset the page size

            this.future = {};
            this.loadAudits(this.getStartAuditsUrl(), DIRECTION.START);
        },
        loadFail: function(errorText) {
            this.fire('ajax-end', {success: false, errorText: errorText});
        },
        loadSuccess: function() {
            this.fire('ajax-end', {success: true});
        },

        getStartAuditsUrl: function() {
            var url = vimmaApiAuditList;
            var params = [];
            params.push('min_level=' +
                    encodeURIComponent(this.auditLevels[this.minLevelIdx].id));
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
            return url;
        },

        loadAudits: function(url, direction) {
            var first_right;
            if (direction == DIRECTION.RIGHT) {
                first_right = this.firstItemNr + this.apiResult.results.length;
            }

            var ok = (function(arr) {
                this.future.apiResult = arr[0];

                var first_start = this.future.apiResult.count ? 1 : 0,
                    first_left = this.firstItemNr - this.future.apiResult.results.length;

                switch (direction) {
                case DIRECTION.START:
                    this.future.firstItemNr = first_start;
                    break;
                case DIRECTION.LEFT:
                    this.future.firstItemNr = first_left;
                    break;
                case DIRECTION.RIGHT:
                    this.future.firstItemNr = first_right;
                    break;
                default:
                    this.loadFail('Unknown direction ' + direction);
                    return;
                }

                this.loadMissingUsers();
            }).bind(this);
            apiGet([url], ok, this.loadFail.bind(this));
        },

        loadMissingUsers: function() {
            var allUserIds = {};
            this.future.apiResult.results.forEach(function(r) {
                if (!r.user) {
                    return;
                }
                allUserIds[r.user] = null;
            });

            this.future.usersById = {};
            var missingUserIds = {};
            Object.keys(allUserIds).forEach(function(x) {
                if (!this.usersById || !(x in this.usersById)) {
                    missingUserIds[x] = null;
                } else {
                    this.future.usersById[x] = this.usersById[x];
                }
            }, this);

            var urls = [];
            Object.keys(missingUserIds).forEach(function(x) {
                urls.push(vimmaApiUserDetailRoot + x + '/');
            });

            var ok = (function(arr) {
                arr.forEach(function(x) {
                    this.future.usersById[x.id] = x;
                }, this);

                ['apiResult', 'firstItemNr', 'usersById'].forEach(function(field) {
                    this[field] = this.future[field];
                }, this);
                this.loadSuccess();
            }).bind(this);
            apiGet(urls, ok, this.loadFail.bind(this));
        },

        loadPrevious: function() {
            this.fire('ajax-start');
            this.future = {};
            this.loadAudits(this.apiResult.previous, DIRECTION.LEFT);
        },
        loadNext: function() {
            this.fire('ajax-start');
            this.future = {};
            this.loadAudits(this.apiResult.next, DIRECTION.RIGHT);
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
        },
        getUserTooltip: function(userId) {
            if (userId == null) {
                return '';
            }
            if (!(userId in this.usersById)) {
                return userId + '?';
            }
            var u = this.usersById[userId];
            return u.first_name + ' ' + u.last_name;
        },

        getLastItemNr: function() {
            return this.firstItemNr +
                Math.max(0, this.apiResult.results.length-1);
        },

        minLevelChanged: function(ev, detail, sender) {
            this.minLevelIdx = sender.selectedIndex;
            this.reload();
        }
    });
})();
