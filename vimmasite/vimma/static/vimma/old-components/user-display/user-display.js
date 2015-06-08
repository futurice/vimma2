Polymer('user-display', {
    userid: -1,

    user: null,

    loading: true,
    loadingSucceeded: false,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');

        this.loading = true;

        this.user = null;

        this.loadUser();
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

    loadUser: function() {
        var ok = (function(resultArr) {
            this.user = resultArr[0];
            this.loadSuccess();
        }).bind(this);

        var url = vimmaApiUserDetailRoot + this.userid + '/';
        apiGet([url], ok, this.loadFail.bind(this));
    }
});
