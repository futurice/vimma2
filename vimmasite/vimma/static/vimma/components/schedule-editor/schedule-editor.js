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
        'editModel.timezone': 'editTzChanged',
        'editModel.is_special': 'checkUnsavedChanges',
        'editModel.matrix': 'checkUnsavedChanges',
        'savedModel': 'checkUnsavedChanges'
    },

    tzIdx: null,
    tzIdxChanged: function() {
        this.editModel.timezone = this.timezones[this.tzIdx].id;
    },

    editTzChanged: function() {
        this.timezones.forEach((function(tz, idx) {
            if (tz.id == this.editModel.timezone) {
                this.tzIdx = idx;
            }
        }).bind(this));
        this.checkUnsavedChanges();
    },

    hasUnsavedChanges: false,
    checkUnsavedChanges: function() {
        this.hasUnsavedChanges = !sameModels(this.savedModel, this.editModel);
    },

    delete: function() {
        if (!confirm('Delete schedule ‘' + this.savedModel.name + '’?')) {
            return;
        }
        this.$.ajax.fire('start');
        $.ajax({
            url: vimmaApiScheduleDetailRoot + this.editModel.id + '/',
            type: 'DELETE',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
                this.fire('schedule-deleted');
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    },

    revert: function() {
        this.editModel = clone(this.savedModel);
    },

    save: function() {
        this.$.ajax.fire('start');
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
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
                this.savedModel = clone(this.editModel);
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    }
});
