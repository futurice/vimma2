Polymer('schedule-list', {
    loading: true,
    success: null,
    errorText: null,
    schedules: null,
    timezones: null,

    newScheduleName: '',
    newScheduleTimeZone: null,

    ajaxInProgress: false,
    ajaxSuccess: true,
    ajaxErrTxt: '',

    created: function() {
        var success = (function(resultsArr) {
            this.loading = false;
            this.success = true;
            this.schedules = resultsArr[0];
            this.timezones = resultsArr[1];
        }).bind(this);

        var fail = (function(errorText) {
            this.loading = false;
            this.success = false;
            this.errorText = errorText;
        }).bind(this);

        apiGetAll([vimmaApiScheduleList, vimmaApiTimeZoneList], success, fail);

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

    scheduleDeleted: function(e, detail, sender) {
        var arrayIdx = parseInt(sender.getAttribute('arrayIdx'));
        this.schedules.splice(arrayIdx, 1);
    },
    nameEdited: function(e, detail, sender) {
        sender.commit();
    },

    timezoneSelected: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.newScheduleTimeZone = parseInt(
                    detail.item.getAttribute('tzid'), 10);
        }
    },

    create: function() {
        this.ajaxInProgress = true;

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
            complete: (function() {
                this.ajaxInProgress = false;
            }).bind(this),
            success: (function(data) {
                this.ajaxSuccess = true;
                this.schedules.push(data);
                this.newScheduleName = '';
            }).bind(this),
            error: (function(xhr, txtStatus, saveErr) {
                this.ajaxSuccess = false;
                this.ajaxErrTxt = getAjaxErr.apply(this, arguments);
            }).bind(this)
        });
    }
});
