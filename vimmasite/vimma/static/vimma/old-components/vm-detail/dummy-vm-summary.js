Polymer('dummy-vm-summary', {
    /* same as for <vm-detail> */
    loading: true,
    loadingSucceeded: false,

    vm: null,
    dummyvm: null,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');
        this.loading = true;

        this.vm = null;
        this.dummyvm = null;

        this.loadVM();
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
