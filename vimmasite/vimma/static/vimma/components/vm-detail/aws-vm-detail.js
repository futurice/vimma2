Polymer('aws-vm-detail', {
    /* same as for <vm-detail> */
    loading: true,
    loadingSucceeded: false,

    vm: null,
    awsvm: null,
    provider: null,
    awsprovider: null,

    attached: function() {
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');
        this.loading = true;

        this.vm = null;
        this.awsvm = null;

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
            this.awsvm = resultArr[1].results[0];
            this.loadProvider();
        }).bind(this);
        apiGet([vimmaApiVMDetailRoot + this.vmid + '/',
                vimmaApiAWSVMDetailRoot + '?vm=' + this.vmid],
                ok, this.loadFail.bind(this));
    },
    loadProvider: function() {
        var ok = (function(resultArr) {
            this.provider = resultArr[0];
            this.awsprovider = resultArr[1].results[0];
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiProviderDetailRoot + this.vm.provider + '/',
                vimmaApiAWSProviderDetailRoot + '?provider=' + this.vm.provider],
                ok, this.loadFail.bind(this));
    }
});
