Polymer('schedule-list', {
    loading: true,
    success: null,
    errorText: null,
    schedules: null,

    created: function() {
        var success = (function(schedules) {
            this.loading = false;
            this.success = true;
            this.schedules = schedules;
        }).bind(this);

        var fail = (function(errorText) {
            this.loading = false;
            this.success = false;
            this.errorText = errorText;
        }).bind(this);

        apiGetAll(vimmaApiScheduleList, success, fail);
    }
});
