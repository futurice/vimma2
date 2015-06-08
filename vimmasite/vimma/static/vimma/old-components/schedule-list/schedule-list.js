Polymer('schedule-list', {
    loading: true,
    loadingSucceeded: false,

    schedules: null,
    timezones: null,

    newScheduleName: '',
    newScheduleTimeZone: null,
    tzIdx: null,
    tzIdxChanged: function() {
        var tz = this.timezones[this.tzIdx];
        this.newScheduleTimeZone = tz ? tz.id : null;
    },

    created: function() {
        this.defaultMatrix = [];
        var i, j, row;
        for (i = 0; i < 7; i++) {
            row = [];
            for (j = 0; j < 48; j++) {
                row.push(false);
            }
            this.defaultMatrix.push(row);
        }
    },

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');
        this.loading = true;

        this.vm = null;
        this.awsvm = null;

        this.loadSchedTz();
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

    loadSchedTz: function() {
        var ok = (function(resultsArr) {
            this.schedules = resultsArr[0];
            this.timezones = resultsArr[1];
            this.loadSuccess();
        }).bind(this);
        apiGetAll([vimmaApiScheduleList, vimmaApiTimeZoneList],
            ok, this.loadFail.bind(this));
    },

    scheduleDeleted: function(e, detail, sender) {
        var arrayIdx = parseInt(sender.getAttribute('arrayIdx'));
        this.schedules.splice(arrayIdx, 1);
    },

    create: function() {
        this.$.ajax.fire('start');

        $.ajax({
            url: vimmaApiScheduleList,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                name: this.newScheduleName,
                timezone: this.newScheduleTimeZone,
                matrix: JSON.stringify(this.defaultMatrix)
            }),
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
                this.schedules.unshift(data);
                this.newScheduleName = '';
                this.tzIdx = null;
                this.toggleCreateSchedule();
            }).bind(this),
            error: (function(xhr, txtStatus, saveErr) {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    },

    showCreateSchedule: false,
    toggleCreateSchedule: function() {
        this.showCreateSchedule = !this.showCreateSchedule;
    }
});
