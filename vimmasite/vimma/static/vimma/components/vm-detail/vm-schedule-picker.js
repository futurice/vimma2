Polymer('vm-schedule-picker', {
    loading: true,
    loadingSucceeded: false,

    vm: null,
    vmChanged: function() {
        this.newSchedId = this.vm ? this.vm.schedule : null;
    },
    schedules: null,

    // the schedule ID selected by the user
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

    schedSelected: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.newSchedId = detail.item.templateInstance.model.s.id;
        }
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
