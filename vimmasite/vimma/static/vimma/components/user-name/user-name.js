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

        // The error string or the empty string if there is no error
        _error: String,

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
        /* Hack: prevent hitting an invalid url ‘…/null/…’.
         * This component currently requires a valid user id. Although
         * <audit-display> uses it correctly, inside a ‘dom-if’, when it
         * changes the page of audits (e.g. change the minimum log level)
         * and some audit rows don't have a user anymore, the existing
         * <user-name> component receives a binding change, even though it's
         * inside a ‘dom-if restamp’ which is now false.
         */
        if (userid === null) {
            return null;
        }

        return vimmaApiUserDetailRoot + userid + '/?format=json';
    },

    _computeView: function(loading, error) {
        if (loading) {
            return this._viewLoading;
        }
        if (error) {
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
