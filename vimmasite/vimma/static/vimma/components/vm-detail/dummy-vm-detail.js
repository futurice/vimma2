Polymer('dummy-vm-detail', {
    vm: null,
    dummyvm: null,

    loading: true,
    success: null,
    errorText: null,

    /*
     * The VM is loaded and performing an AJAX operation, e.g. requesting a
     * reboot.
     */
    ajaxInProgress: false,
    ajaxSuccess: true,
    ajaxErrTxt: '',

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
    },

    ajaxRequest: function(url, data) {
        this.ajaxInProgress = true;
        $.ajax({
            url: url,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                vmid: this.vm.id,
                data: data
            }),
            complete: (function(data) {
                this.ajaxInProgress = false;
            }).bind(this),
            success: (function(data) {
                this.ajaxSuccess = true;
            }).bind(this),
            error: (function() {
                this.ajaxSuccess = false;
                this.ajaxErrTxt = getAjaxErr.apply(this, arguments);
            }).bind(this)
        });
    },

    powerOn: function() {
        this.ajaxRequest(vimmaEndpointPowerOnVM, null);
    },
    powerOff: function() {
        this.ajaxRequest(vimmaEndpointPowerOffVM, null);
    },
    reboot: function() {
        this.ajaxRequest(vimmaEndpointRebootVM, null);
    },
    destroy: function() {
        this.ajaxRequest(vimmaEndpointDestroyVM, null);
    }
});
