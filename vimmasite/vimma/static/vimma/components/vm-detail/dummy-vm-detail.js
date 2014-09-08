Polymer('dummy-vm-detail', {
    vm: null,
    dummyvm: null,

    loading: true,
    success: null,
    errorText: null,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.loading = true;
        this.success = null;
        this.errorText = null;

        this.vm = null;
        this.dummyvm = null;

        this.loadVM();
    },
    loadFail: function(errorText) {
        this.loading = false;
        this.success = false;
        this.errorText = errorText;
    },
    loadSuccess: function() {
        this.loading = false;
        this.success = true;
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
