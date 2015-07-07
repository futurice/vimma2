Polymer({
    is: 'vm-schedule',

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        vmid: {
            type: Number,
            observer: '_vmidChanged'
        },

        _loadingToken: Object,  // same logic as in <vm-list>
        _loading: Boolean,
        _loadErr: String,
        _vm: {
            type: Array,
            observer: '_vmChanged'
        },
        _schedules: Array,

        _newSchedId: Number,

        _unsavedChanges: {
            type: Boolean,
            computed: '_computeUnsavedChanges(_vm, _newSchedId)'
        },

        _actionInFlight: Boolean,
        _actionErr: String
    },

    _vmidChanged: function(newV, oldV) {
        this._reload();
    },

    _reload: function() {
        var token = {};
        this._loadingToken = token;
        this._loading = true;
        this._actionInFlight = false;
        this._actionErr = '';

        var vmUrl = vimmaApiVMDetailRoot + this.vmid + '/';

        apiGet([vmUrl], vmSuccess.bind(this), fail.bind(this));

        function fail(err) {
            if (this._loadingToken != token) {
                return;
            }

            this._loadErr = err;
            this._loading = false;
        }

        function vmSuccess(resArr) {
            if (this._loadingToken != token) {
                return;
            }

            this._vm = resArr[0];

            apiGetAll([vimmaApiScheduleList],
                    schedSuccess.bind(this), fail.bind(this));

            function schedSuccess(resArr) {
                if (this._loadingToken != token) {
                    return;
                }

                this._schedules = resArr[0];
                this._loadErr = '';
                this._loading = false;
            }
        }
    },

    _scheduleChanged: function(ev) {
        this._newSchedId = this._schedules[ev.target.selectedIndex].id;
    },

    _vmChanged: function(newV, oldV) {
        this._newSchedId = newV.schedule;
    },

    _computeUnsavedChanges: function(vm, newSchedId) {
        return vm.schedule !== newSchedId;
    },
    _getButtonClass: function(unsavedChanges) {
        if (unsavedChanges) {
            return 'unsaved';
        }
        return '';
    },

    _save: function() {
        var token = this._loadingToken;
        this._actionInFlight = true;

        $.ajax({
            url: vimmaEndpointChangeVMSchedule,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                vmid: this.vmid,
                scheduleid: this._newSchedId
            }),
            complete: (function() {
                if (this._loadingToken != token) {
                    return;
                }

                this._actionInFlight = false;
            }).bind(this),
            success: (function(data) {
                if (this._loadingToken != token) {
                    return;
                }

                this._reload();
            }).bind(this),
            error: (function() {
                if (this._loadingToken != token) {
                    return;
                }

                var errorText = getAjaxErr.apply(this, arguments);
                this._actionErr = errorText;
            }).bind(this)
        });
    }
});
