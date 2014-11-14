Polymer('vm-schedule-picker', {
    loading: true,
    loadingSucceeded: false,

    observe: {
        vm: 'setNewSchedIdx',
        schedules: 'setNewSchedIdx'
    },

    vm: null,
    schedules: null,

    setNewSchedIdx: function() {
        this.newSchedIdx = null;
        if (this.vm && this.schedules) {
            this.schedules.forEach((function(s, idx) {
                if (s.id == this.vm.schedule) {
                    this.newSchedIdx = idx;
                }
            }).bind(this));
        }
    },
    // the index of the schedule selected by the user
    newSchedIdx: null,
    newSchedIdxChanged: function() {
        this.newSchedId = this.newSchedIdx == null ? null :
            this.schedules[this.newSchedIdx].id;
    },
    newSchedId: null,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');

        this.loading = true;

        this.vm = null;
        this.schedules = null;

        this.loadVm();
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

    loadVm: function() {
        var ok = (function(resultArr) {
            this.vm = resultArr[0];
            this.loadSchedules();
        }).bind(this);
        apiGet([vimmaApiVMDetailRoot + this.vmid + '/'],
                ok, this.loadFail.bind(this));
    },
    loadSchedules: function() {
        var ok = (function(resultArr) {
            this.schedules = resultArr[0];
            this.loadSuccess();
        }).bind(this);
        apiGetAll([vimmaApiScheduleList],
            ok, this.loadFail.bind(this));
    },

    save: function() {
        this.$.ajax.fire('start');
        $.ajax({
            url: vimmaEndpointChangeVMSchedule,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                vmid: this.vmid,
                scheduleid: this.newSchedId
            }),
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
                this.reload();
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    }
});
