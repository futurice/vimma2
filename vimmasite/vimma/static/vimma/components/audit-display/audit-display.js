(function() {
    // Direction followed when loading a new Audit page.
    var DIRECTION = {
        START: 'start',
        LEFT: 'left',
        RIGHT: 'right'
    };

    Polymer('audit-display', {
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
        // can't refer to ‘restMaxPageSize’ in the template disabled?= binding
        maxPageSize: restMaxPageSize,

        ready: function() {
            this.reload();
        },

        reload: function() {
            this.$.ajax.fire('start');

            this.apiResult = null;
            this.firstItemNr = 1;
            this.usersById = null;
            // don't reset the page size

            this.future = {};
            this.loadAudits(this.getStartAuditsUrl(), DIRECTION.START);
        },
        loadFail: function(errorText) {
            this.$.ajax.fire('end', {success: false, errorText: errorText});
        },
        loadSuccess: function() {
            this.$.ajax.fire('end', {success: true});
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
            params.push(restPageSizeQueryParam + '=' + this.pageSize);
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
            this.$.ajax.fire('start');
            this.future = {};
            this.loadAudits(this.apiResult.previous, DIRECTION.LEFT);
        },
        loadNext: function() {
            this.$.ajax.fire('start');
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
            // loading is in progress, return some dummy value
            if (!this.apiResult) {
                return 0;
            }

            return this.firstItemNr +
                Math.max(0, this.apiResult.results.length-1);
        },

        minLevelChanged: function(ev, detail, sender) {
            this.minLevelIdx = sender.selectedIndex;
            this.reload();
        },

        getAuditLevelName: function(lvl) {
            if (lvl in auditNameForLevel) {
                return auditNameForLevel[lvl];
            }
            console.log('Unknown audit level ‘' + lvl + '’');
            return lvl;
        }
    });
})();
