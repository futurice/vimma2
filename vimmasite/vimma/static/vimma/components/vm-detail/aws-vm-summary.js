Polymer('aws-vm-summary', {
    /* same as for <vm-detail> */
    loading: true,
    loadingSucceeded: false,

    vm: null,
    awsvm: null,
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
            this.awsprovider = resultArr[0].results[0];
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiAWSProviderList + '?provider=' + this.vm.provider],
            ok, this.loadFail.bind(this));
    }
});
