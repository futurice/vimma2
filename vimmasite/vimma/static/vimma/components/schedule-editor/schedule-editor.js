Polymer('schedule-editor', {
    ready: function() {
        // The external interface is ‘model’. Internally we have a last saved
        // model and the current editing model.
        this.savedModel = clone(this.model);
        this.savedModel.matrix = JSON.parse(this.savedModel.matrix);
        this.editModel = clone(this.savedModel);

        this.model = null;
    },

    observe: {
        'editModel.name': 'checkUnsavedChanges',
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
                this.savedModel = this.editModel;
            }).bind(this),
            error: (function() {
                this.ajaxSuccess = false;
                this.ajaxErrTxt = getAjaxErr.apply(this, arguments);
            }).bind(this)
        });
    }
});
