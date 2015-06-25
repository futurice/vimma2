Polymer({
    is: 'ajax-load',

    properties: {
        url: String,

        // Making this read-only means we can't bind it to the child component
        // and get updates. Using _ironLoading for that.
        loading: {
            type: Boolean,
            notify: true,
            computed: '_computeLoading(_ironLoading)'
        },

        // only defined if loading is false
        error: {
            type: String,
            readOnly: true,
            notify: true,
            value: ''
        },

        // only defined if loading is false and error is ''
        data: {
            type: Object,
            readOnly: true,
            notify: true
        },

        _ironLoading: Boolean
    },

    _computeLoading: function(ironLoading) {
        return ironLoading;
    },

    _handleError: function(ev) {
        if (ev.detail.request !== this.$.ajax.lastRequest) {
            return;
        }
        this._setError(ev.detail.error.message);
    },
    _handleResponse: function(ev) {
        if (ev.detail !== this.$.ajax.lastRequest) {
            return;
        }
        // net::ERR_CONNECTION_REFUSED triggers on-response with null response.
        // https://github.com/PolymerElements/iron-ajax/issues/63
        if (ev.detail.response === null) {
            if (ev.detail.xhr.status === 0) {
                this._setError('Error (cannot connect?)');
            } else {
                // trigger this by putting a long delay in the endpoint and
                // killing the server during that delay.
                this._setError('Error (invalid response)');
            }
            return;
        }

        this._setError('');
        this._setData(ev.detail.response);
    }
});
