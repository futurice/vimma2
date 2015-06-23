// See <audit-display> for the current limitations of <iron-ajax> which
// require more error-handling code on our part.
Polymer({
    is: 'user-name',

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        userid: Number,

        show: {
            type: String,
            value: function() { return this.properties._showFull.value; }
        },
        _showFull: {
            type: String,
            readOnly: true,
            value: 'full'
        },
        _showName: {
            type: String,
            readOnly: true,
            value: 'name'
        },
        _showUsername: {
            type: String,
            readOnly: true,
            value: 'username'
        },

        _url: {
            type: String,
            computed: '_computeUrl(userid)'
        },

        _loading: Boolean,

        // The error string or ‘null’ if there is no error
        _error: {
            type: String,
            value: null
        },

        _user: Object,

        _view: {
            type: String,
            computed: '_computeView(_loading, _error)'
        },
        _viewLoading: {
            type: String,
            readOnly: true,
            value: 'loading'
        },
        _viewError: {
            type: String,
            readOnly: true,
            value: 'error'
        },
        _viewUser: {
            type: String,
            readOnly: true,
            value: 'user'
        },

        _text: {
            type: String,
            computed: '_computeText(_user, show)'
        },
        _tooltip: {
            type: String,
            computed: '_computeTooltip(_user, show)'
        }
    },

    _computeUrl: function(userid) {
        return vimmaApiUserDetailRoot + userid + '/?format=json';
    },

    _handleError: function(ev) {
        if (ev.detail.request !== this.$.ajax.lastRequest) {
            return;
        }
        this._error = ev.detail.error.message;
    },
    _handleResponse: function(ev) {
        if (ev.detail !== this.$.ajax.lastRequest) {
            return;
        }
        if (ev.detail.response === null) {
            if (ev.detail.xhr.status === 0) {
                this._error = 'Error (cannot connect?)';
            } else {
                this._error = 'Error (invalid response)';
            }
            return;
        }

        this._error = null;
        this._user = ev.detail.response;
    },

    _computeView: function(loading, error) {
        if (loading) {
            return this._viewLoading;
        }
        if (error != null) {
            return this._viewError;
        }
        return this._viewUser;
    },

    _computeText: function(user, show) {
        switch (show) {
            case this._showName:
                return user.first_name + ' ' + user.last_name;
            case this._showUsername:
                return user.username;
            default:
                return user.first_name + ' ' + user.last_name + ' (' +
                        user.username + ')';
        }
    },

    _computeTooltip: function(user, show) {
        switch (show) {
            case this._showName:
                return user.username;
            case this._showUsername:
                return user.first_name + ' ' + user.last_name;
            default:
                return '';
        }
    }
});
