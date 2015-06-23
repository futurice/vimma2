Polymer({
    is: 'audit-display',

    // https://github.com/PolymerElements/iron-ajax/issues/63
    // If <iron-ajax> will treat connection errors like errors (it currently
    // treats them as successful responses) we will be able to make a more
    // elegant data model, computing a few properties from its loading,
    // lastRequest, lastError (e.g. to check if lastError refers to
    // lastRequest).
    // As it is now, we're using success&error handling functions to set and
    // clear the error ourselves.

    properties: {
        vmid: {
            type: Number,
            value: -1
        },
        userid: {
            type: Number,
            value: -1
        },

        _auditLevels: {
            type: Number,
            readOnly: true,
            value: auditLevels
        },
        _minLevel: {
            type: Object,
            value: auditLevels[1]
        },

        pageSize: {
            type: Number,
            value: 5
        },

        _maxPageSize: {
            type: Number,
            readOnly: true,
            value: 100
        },

        // the first page of results
        _startUrl: {
            type: String,
            computed: '_computeStartUrl(vmid, userid, _minLevel, pageSize)',
            observer: '_startUrlChanged'
        },

        // the current page of results
        _currentUrl: String,

        _loading: Boolean,

        // The error string or ‘null’ if there is no error
        _error: {
            type: String,
            value: null
        },

        _data: {
            type: Object,
            value: null
        },

        _view: {
            type: String,
            computed: '_computeView(_loading, _error, _data)'
        },
        /* constants */
        _viewLoading: {
            type: String,
            value: 'loading',
            readOnly: true
        },
        _viewError: {
            type: String,
            value: 'error',
            readOnly: true
        },
        _viewData: {
            type: String,
            value: 'data',
            readOnly: true
        },

        _firstItemNr: {
            type: Number,
            value: 1
        }
    },

    // <select> ‘change’ event
    _minLevelChange: function(ev) {
        this._minLevel = this._auditLevels[ev.target.selectedIndex];
    },
    _getAuditLvlName: function(lvl) {
        if (lvl in auditNameForLevel) {
            return auditNameForLevel[lvl];
        }
        console.log('Unknown audit level ‘' + lvl + '’');
        return lvl;
    },

    _computeStartUrl: function(vmid, userid, minLvl, pageSize) {
        var url = vimmaApiAuditList,
            params = [];
        params.push('format=json');
        params.push('min_level=' + encodeURIComponent(minLvl.id));
        if (vmid != -1) {
            params.push('vm=' + vmid);
        }
        if (userid != -1) {
            params.push('user=' + userid);
        }
        params.push(restPageSizeQueryParam + '=' + pageSize);

        if (params.length) {
            url += '?' + params.join('&');
        }
        return url;
    },

    _startUrlChanged: function(newV, oldV) {
        this._currentUrl = newV;
        this._firstItemNr = 1;
    },

    handleError: function(ev) {
        if (ev.detail.request !== this.$.ajax.lastRequest) {
            return;
        }
        this._error = ev.detail.error.message;
    },
    handleResponse: function(ev) {
        if (ev.detail !== this.$.ajax.lastRequest) {
            return;
        }
        // net::ERR_CONNECTION_REFUSED triggers on-response with null response.
        // https://github.com/PolymerElements/iron-ajax/issues/63
        if (ev.detail.response === null) {
            if (ev.detail.xhr.status === 0) {
                this._error = 'Error (cannot connect?)';
            } else {
                // trigger this by putting a long delay in the endpoint and
                // killing the server during that delay.
                this._error = 'Error (invalid response)';
            }
            return;
        }

        this._error = null;
        this.set('_data', ev.detail.response);
    },

    _computeView: function(loading, error, data) {
        if (loading) {
            if (data) {
                return this._viewData;
            }
            return this._viewLoading;
        }
        if (error) {
            return this._viewError;
        }
        return this._viewData;
    },

    _reload: function() {
        this.set('_data', null);
        this._currentUrl = null;
        this._currentUrl = this._startUrl;
        this._firstItemNr = 1;
    },

    _prevPage: function() {
        this._currentUrl = this._data.previous;
        this._firstItemNr -= this.pageSize;
    },

    _nextPage: function() {
        this._currentUrl = this._data.next;
        this._firstItemNr += this.pageSize;
    },

    _getLastItemNr: function(firstNr, data) {
        if (!data || !data.results.length) {
            return 0;
        }
        return firstNr + data.results.length - 1;
    },

    _canShowMore: function(pageSize, maxPageSize) {
        return pageSize < maxPageSize;
    },
    _showMore: function() {
        this.pageSize = Math.min(2*this.pageSize, this._maxPageSize);
    },

    _equal: function(x, y) {
        return x === y;
    }
});
