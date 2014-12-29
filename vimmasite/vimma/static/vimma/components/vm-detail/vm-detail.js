Polymer('vm-detail', {
    /*
     * This component is currently loading its data.
     *
     * This is different from $.ajax.inProgress, whach is true during all
     * AJAX operations (e.g. while loading the initial data; after loading the
     * initial data, while requesting a Reboot of the VM).
     */
    loading: true,
    /*
     * Shows if the most recent attempt to load the component's data succeeded.
     */
    loadingSucceeded: false,

    vmid: null,
    vm: null,
    provider: null,
    project: null,

    overrideSchedMins: 10,
    overrideSchedStateIdx: 0,
    showLogs: true,
    showPowerLog: true,
    initiallyExpanded: false,

    ready: function() {
        // what the schedule-override will be, if the user sets one
        this.overrideSchedStates = [
            {key: true, label: 'Powered ON'},
            {key: false, label: 'Powered OFF'}
        ];

        this.expanded = this.initiallyExpanded;
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');

        this.loading = true;

        this.vm = null;
        this.provider = null;
        this.project = null;
        // keep this.expanded, this.showLogs and this.showPowerLog
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
            this.loadProvPrj();
        }).bind(this);
        apiGet([vimmaApiVMDetailRoot + this.vmid + '/'],
                ok, this.loadFail.bind(this));
    },
    loadProvPrj: function() {
        var ok = (function(resultArr) {
            this.provider = resultArr[0];
            this.project = resultArr[1];
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiProviderDetailRoot + this.vm.provider + '/',
                vimmaApiProjectDetailRoot + this.vm.project + '/'],
                ok, this.loadFail.bind(this));
    },

    // could be better named
    vmOperation: function(url, confirmText, data) {
        if (!confirm(confirmText + ' this VM?')) {
            return;
        }
        this.$.ajax.fire('start');
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
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    },

    reboot: function() {
        this.vmOperation(vimmaEndpointRebootVM, 'Reboot', null);
    },
    destroy: function() {
        this.vmOperation(vimmaEndpointDestroyVM, 'Destroy', null);
    },

    tstampToString: function(ts) {
        return new Date(ts * 1000).toString();
    },
    ajaxOverrideSchedule: function(jsonBody) {
        this.$.ajax.fire('start');
        $.ajax({
            url: vimmaEndpointOverrideSchedule,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify(jsonBody),
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
                this.reload();
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    },
    overrideSet: function() {
        this.ajaxOverrideSchedule({
            vmid: this.vm.id,
            state: this.overrideSchedStates[this.overrideSchedStateIdx].key,
            seconds: Math.floor(this.overrideSchedMins * 60)
        });
    },
    overrideClear: function() {
        this.ajaxOverrideSchedule({vmid: this.vm.id, state: null});
    },

    toggleShowLogs: function() {
        this.showLogs = !this.showLogs;
    },

    toggleShowPowerLog: function() {
        this.showPowerLog = !this.showPowerLog;
    },

    toggleExpanded: function() {
        this.expanded = !this.expanded;
        this.fire(this.expanded ? 'vm-expanded' : 'vm-collapsed');
    },
});
