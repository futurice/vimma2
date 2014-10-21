Polymer('vm-detail', {
    /*
     * Global indicator (for this component and its <type-specific> children)
     * of the most recent AJAX operation.
     *
     * Children and the parent signal the start and end via the 'ajax-start'
     * and 'ajax-end' ({success: true} or {success: false, errorText: string})
     * events.
     *
     * The component informs children of the state via their ajaxInProgress
     * attribute (property?). Children may not write to this property.
     *
     * While an AJAX operation is in progress, all components (the parent and
     * the type-specific children) disable UI elements (buttons, input fields)
     * and may not start another AJAX operation (either initiated by the user
     * or initiated by a periodic operation, e.g. a refresh that happens every
     * 10 seconds).
     */
    ajaxInProgress: false,
    ajaxSuccess: true,
    ajaxErrTxt: '',

    onAjaxStart: function(ev) {
        ev.stopPropagation();
        if (this.ajaxInProgress) {
            throw 'ajax-start fired while ajaxInProgress';
        }
        this.ajaxInProgress = true;
    },

    onAjaxEnd: function(ev, detail, sender) {
        ev.stopPropagation();
        if (!this.ajaxInProgress) {
            throw 'ajax-end fired while not ajaxInProgress';
        }
        this.ajaxInProgress = false;
        this.ajaxSuccess = detail.success;
        this.ajaxErrTxt = this.ajaxSuccess ? '' : detail.errorText;
    },

    /*
     * This component is currently loading its data.
     *
     * This is different from ajaxInProgress. ajaxInProgress is true during all
     * AJAX operations. E.g. while loading the initial data; after loading the
     * initial data, while requesting a Reboot of the VM.
     */
    loading: true,
    /*
     * Shows if the most recent attempt to load the component's data succeeded.
     */
    loadingSucceeded: false,

    vmid: null,
    vm: null,
    provider: null,
    schedule: null,
    // what the schedule-override will be, if the user sets one
    overrideSchedState: 'on',
    overrideSchedMins: 10,
    showLogs: false,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.fire('ajax-start');

        this.loading = true;

        this.vm = null;
        this.provider = null;
        this.schedule = null;
        this.showLogs = false;

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
            this.loadProviderAndSchedule();
        }).bind(this);
        apiGet([vimmaApiVMDetailRoot + this.vmid + '/'],
                ok, this.loadFail.bind(this));
    },
    loadProviderAndSchedule: function() {
        var ok = (function(resultArr) {
            this.provider = resultArr[0];
            this.schedule = resultArr[1];
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiProviderDetailRoot + this.vm.provider + '/',
                vimmaApiScheduleDetailRoot + this.vm.schedule + '/'],
                ok, this.loadFail.bind(this));
    },

    // could be better named
    vmOperation: function(url, data) {
        this.fire('ajax-start');
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
                this.fire('ajax-end', {success: true});
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.fire('ajax-end', {success: false, errorText: errorText});
            }).bind(this)
        });
    },

    powerOn: function() {
        this.vmOperation(vimmaEndpointPowerOnVM, null);
    },
    powerOff: function() {
        this.vmOperation(vimmaEndpointPowerOffVM, null);
    },
    reboot: function() {
        this.vmOperation(vimmaEndpointRebootVM, null);
    },
    destroy: function() {
        this.vmOperation(vimmaEndpointDestroyVM, null);
    },

    overrideSchedStateSelected: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.overrideSchedState = detail.item.getAttribute('key');
        }
    },
    tstampToString: function(ts) {
        return new Date(ts * 1000).toString();
    },
    ajaxOverrideSchedule: function(jsonBody) {
        this.fire('ajax-start');
        $.ajax({
            url: vimmaEndpointOverrideSchedule,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify(jsonBody),
            success: (function(data) {
                this.fire('ajax-end', {success: true});
                this.reload();
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.fire('ajax-end', {success: false, errorText: errorText});
            }).bind(this)
        });
    },
    overrideSet: function() {
        this.ajaxOverrideSchedule({
            vmid: this.vm.id,
            state: this.overrideSchedState == 'on',
            seconds: this.overrideSchedMins * 60
        });
    },
    overrideClear: function() {
        this.ajaxOverrideSchedule({vmid: this.vm.id, state: null});
    },

    toggleShowLogs: function() {
        this.showLogs = !this.showLogs;
    }
});
