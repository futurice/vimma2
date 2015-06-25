Polymer({
    is: 'api-loader',

    properties: {
        url: {
            type: String,
            observer: '_urlChanged'
        },

        loading: {
            type: Boolean,
            notify: true,
            readOnly: true,
            value: false
        },

        // The error or an empty string; not defined if loading==false.
        error: {
            type: String,
            notify: true,
            readOnly: true,
            value: ''
        },

        // The API results; only defined if loading==false and error==''.
        data: {
            type: Object,
            notify: true,
            readOnly: true,
            value: function() {
                return [];
            }
        },

        // An object indicating the most recent request.
        _lastRequest: {
            type: Object
        }
    },

    _urlChanged: function(newV, oldV) {
        this._setLoading(true);
        var thisReq = {};
        this._lastRequest = thisReq;

        var ok = (function(resultsArray) {
            if (this._lastRequest != thisReq) {
                return;
            }

            this._setData(resultsArray[0]);
            this._setError('');
            this._setLoading(false);
        }).bind(this);

        var fail = (function(errorText) {
            if (this._lastRequest != thisReq) {
                return;
            }

            this._setError(errorText);
            this._setLoading(false);
        }).bind(this);

        apiGetAll([newV], ok, fail);
    }
});
