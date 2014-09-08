Polymer('vm-detail', {
    vmid: null,
    loading: true,
    success: null,
    errorText: null,

    vm: null,
    provider: null,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.loading = true;
        this.success = null;
        this.errorText = null;

        this.vm = null;
        this.provider = null;

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
            this.loadProvider();
        }).bind(this);
        apiGet([vimmaApiVMDetailRoot + this.vmid + '/'],
                ok, this.loadFail.bind(this));
    },
    loadProvider: function() {
        var ok = (function(resultArr) {
            this.provider = resultArr[0];
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiProviderDetailRoot + this.vm.provider + '/'],
                ok, this.loadFail.bind(this));
    }
});
