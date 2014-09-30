Polymer('dummy-vm-detail', {
    /* same as for <vm-detail> */
    loading: true,
    loadingSucceeded: null,

    vm: null,
    dummyvm: null,

    attached: function() {
        this.reload();
    },

    reload: function() {
        this.fire('ajax-start');
        this.loading = true;
        this.loadingSucceeded = null;

        this.vm = null;
        this.dummyvm = null;

        this.loadVM();
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

    loadVM: function() {
        var ok = (function(resultArr) {
            this.vm = resultArr[0];
            this.dummyvm = resultArr[1].results[0];
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiVMDetailRoot + this.vmid + '/',
                vimmaApiDummyVMDetailRoot + '?vm=' + this.vmid],
                ok, this.loadFail.bind(this));
    }
});
