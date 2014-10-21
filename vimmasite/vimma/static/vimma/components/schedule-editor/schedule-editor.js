Polymer('schedule-editor', {
    created: function() {
        this.matrixRowLabels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday'];
        this.matrixColLabels = [];
        var i;
        for (i = 0; i < 24; i++) {
            this.matrixColLabels.push(i + ':00 → ' + i + ':30');
            this.matrixColLabels.push(i + ':30 → ' + ((i+1) % 24) + ':00');
        }
    },
    ready: function() {
        // The external interface is ‘schedule’. Internally we have a last
        // saved model and the currently editing model.
        this.savedModel = clone(this.schedule);
        this.savedModel.matrix = JSON.parse(this.savedModel.matrix);
        this.editModel = clone(this.savedModel);

        this.schedule = null;
    },

    observe: {
        'editModel.name': 'checkUnsavedChanges',
        'editModel.timezone': 'checkUnsavedChanges',
        'editModel.is_special': 'checkUnsavedChanges',
        'editModel.matrix': 'checkUnsavedChanges',
        'savedModel': 'checkUnsavedChanges'
    },

    hasUnsavedChanges: false,
    checkUnsavedChanges: function() {
        this.hasUnsavedChanges = !sameModels(this.savedModel, this.editModel);
    },

    nameEdited: function(e, detail, sender) {
        sender.commit();
    },

    timezoneSelected: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.editModel.timezone = parseInt(
                    detail.item.getAttribute('tzid'), 10);
        }
    },

    ajaxInProgress: false,
    ajaxSuccess: true,
    ajaxErrTxt: '',

    delete: function() {
        this.ajaxInProgress = true;
        $.ajax({
            url: vimmaApiScheduleDetailRoot + this.editModel.id + '/',
            type: 'DELETE',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            complete: (function(data) {
                this.ajaxInProgress = false;
            }).bind(this),
            success: (function(data) {
                this.ajaxSuccess = true;
                this.fire('schedule-deleted');
            }).bind(this),
            error: (function() {
                this.ajaxSuccess = false;
                this.ajaxErrTxt = getAjaxErr.apply(this, arguments);
            }).bind(this)
        });
    },

    revert: function() {
        this.editModel = clone(this.savedModel);
    },

    save: function() {
        this.ajaxInProgress = true;
        $.ajax({
            url: vimmaApiScheduleDetailRoot + this.editModel.id + '/',
            type: 'PUT',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: (function() {
                var dbModel = clone(this.editModel);
                dbModel.matrix = JSON.stringify(dbModel.matrix);
                return JSON.stringify(dbModel);
            }).bind(this)(),
            complete: (function(data) {
                this.ajaxInProgress = false;
            }).bind(this),
            success: (function(data) {
                this.ajaxSuccess = true;
                this.savedModel = clone(this.editModel);
            }).bind(this),
            error: (function() {
                this.ajaxSuccess = false;
                this.ajaxErrTxt = getAjaxErr.apply(this, arguments);
            }).bind(this)
        });
    }
});
