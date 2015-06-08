Polymer('expiration-item', {
    loading: true,
    loadingSucceeded: false,

    expid: null,
    expiration: null,

    newExpiration: null,
    newExpDateStr: null,
    newExpTimeStr: null,
    newExpirationChanged: function() {
        function zeroPref(n) {
            if (n < 10) {
                return '0' + n;
            }
            return n + '';
        }
        var ne = this.newExpiration;
        if (ne) {
            this.newExpDateStr = ne.getFullYear() + '-' + zeroPref(ne.getMonth() + 1) + '-' + zeroPref(ne.getDate());
            this.newExpTimeStr = zeroPref(ne.getHours()) + ':' + zeroPref(ne.getMinutes());
        }
    },

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');

        this.loading = true;

        this.expiration = null;

        this.loadExpiration();
    },
    loadFail: function(errorText) {
        this.$.ajax.fire('end', {success: false, errorText: errorText});

        this.loading = false;
        this.loadingSucceeded = false;
    },
    loadSuccess: function() {
        this.$.ajax.fire('end', {success: true});

        this.loading = false;
        this.loadingSucceeded = true;
    },

    loadExpiration: function() {
        var ok = (function(resultArr) {
            this.expiration = resultArr[0];
            if (this.expiration.vmexpiration != null) {
                this.newExpiration = new Date(new Date().valueOf() + 1000*60*60*24*29);
                this.newExpiration.setHours(12);
                this.newExpiration.setMinutes(0);
            } else {
                // TODO (Mihai): add the 'firewall rule' type and use the durations from settings.py
                console.log('Unknown expiration type');
                this.newExpiration = new Date(new Date().valueOf() + 1000*60*60*24);
            }
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiExpirationDetailRoot + this.expid + '/'],
                ok, this.loadFail.bind(this));
    },

    toggleDialog: function() {
        this.shadowRoot.querySelector("#dialog").toggle();
    },

    setExpiration: function() {
        this.newExpiration = new Date(this.newExpDateStr + ' ' + this.newExpTimeStr);
        this.$.ajax.fire('start');

        $.ajax({
            url: vimmaEndpointSetExpiration,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                id: this.expid,
                timestamp: Math.floor(this.newExpiration.valueOf() / 1000)
            }),
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
                this.reload();
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    }
});
