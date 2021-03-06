Polymer({
    is: 'vm-detail',

    behaviors: [VimmaBehaviors.Equal],

    properties: {
        vmid: {
            type: Number,
            observer: '_vmidChanged'
        },

        // see <schedule-detail>.selectedViaFrag
        selectedViaFrag: {
            type: Boolean,
            observer: '_selectedViaFragChanged'
        },

        _loadingToken: Object,  /* same logic as in <vm-list> */
        _loading: Boolean,
        _error: String, // empty string if no error
        _vm: Object,    // the VM data model

        // User action
        _actionInFlight: {
            type: Boolean,
            value: false
        },
        _actionError: {
            type: String,
            value: ''
        },

        _expanded: {
            type: Boolean,
            value: false,
            observer: '_expandedChanged'
        },

        _showBasicDetails: {
            type: Boolean,
            value: true
        },
        _showScheduleAndExpiry: {
            type: Boolean,
            value: false
        },
        _showFirewallRules: {
            type: Boolean,
            value: false
        },
        _showAdvancedDetails: {
            type: Boolean,
            value: false
        },
        _showLogs: {
            type: Boolean,
            value: false
        },
        _showPowerLog: {
            type: Boolean,
            value: false
        }
    },

    _vmidChanged: function(newV, oldV) {
        this._expanded = this.properties._expanded.value;
        this._reload();
    },

    _selectedViaFragChanged: function(newV, oldV) {
        if (newV) {
            this._expanded = true;
        }
    },

    _reload: function() {
        var token = {};
        this._loadingToken = token;
        this._loading = true;
        this._actionError = '';

        var success = (function(vm) {
            if (this._loadingToken != token) {
                return;
            }

            this._vm = vm;
            this._error = '';
            this._loading = false;
        }).bind(this);

        var fail = (function(err) {
            if (this._loadingToken != token) {
                return;
            }

            this._error = err;
            this._loading = false;
        }).bind(this);

        this.$.vdm.loadVM(this.vmid, success, fail);
    },

    _getShowHideIcon: function(expanded) {
        if (expanded) {
            return 'expand-less';
        }
        return 'expand-more';
    },

    /* Call VMModel methods (we can't do it in the template directly). */
    _getExpiryDate: function(vm) {
        return vm.getExpiryDate();
    },
    _getExpiryClass: function(vm) {
        var d = new Date(vm.getExpiryDate()).valueOf(),
            now = new Date().valueOf(),
            soon = d - now < 1000*60*60*24*30;
        if (d < now) {
            return 'expires-expired';
        }
        if (soon) {
            return 'expires-soon';
        }
        return '';
    },
    _getName: function(vm) {
        return vm.getName();
    },
    _getProjectName: function(vm) {
        return vm.getProjectName();
    },
    _getStateName: function(vm) {
        if (vm.isDestroyed()) {
            return 'Destroyed';
        }
        if (vm.isOn()) {
            return 'Powered ON';
        }
        return 'Powered OFF';
    },
    _getStateIcon: function(vm) {
        if (vm.isDestroyed()) {
            return 'delete';
        }
        if (vm.isOn()) {
            return 'check-circle';
        }
        return 'remove-circle';
    },
    _getStateClass: function(vm) {
        if (vm.isDestroyed()) {
            return 'destroyed';
        }
        if (vm.isOn()) {
            return 'powered-on';
        }
        return 'powered-off';
    },

    _destroy: function(ev) {
        ev.stopPropagation();
        if (!confirm('Destroy VM: ‘' + this._vm.getName() + '’?')) {
            return;
        }

        this._actionInFlight = true;
        $.ajax({
            url: vimmaEndpointDestroyVM,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                vmid: this._vm.vm.id
            }),
            complete: (function() {
                this._actionInFlight = false;
            }).bind(this),
            success: (function(data) {
                this._actionError = '';
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this._actionError = errorText;
            }).bind(this)
        });
    },

    _reboot: function(ev) {
        ev.stopPropagation();
        if (!confirm('Reboot VM: ‘' + this._vm.getName() + '’?')) {
            return;
        }

        this._actionInFlight = true;
        $.ajax({
            url: vimmaEndpointRebootVM,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                vmid: this._vm.vm.id
            }),
            complete: (function() {
                this._actionInFlight = false;
            }).bind(this),
            success: (function(data) {
                this._actionError = '';
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this._actionError = errorText;
            }).bind(this)
        });
    },

    _toggle: function() {
        this._expanded = !this._expanded;
    },

    _expandedChanged: function(newV, oldV) {
        if (this.vmid === undefined) {
            return;
        }

        this.fire(newV ? 'vm-expanded' : 'vm-collapsed', this.vmid);
    },

    _summaryTrack: function() {
    },

    _toggleBasicDetails: function() {
        this._showBasicDetails = !this._showBasicDetails;
    },
    _toggleScheduleAndExpiry: function() {
        this._showScheduleAndExpiry = !this._showScheduleAndExpiry;
    },
    _toggleFirewallRules: function() {
        this._showFirewallRules = !this._showFirewallRules;
    },
    _toggleAdvancedDetails: function() {
        this._showAdvancedDetails = !this._showAdvancedDetails;
    },
    _toggleLogs: function() {
        this._showLogs = !this._showLogs;
    },
    _togglePowerLog: function() {
        this._showPowerLog = !this._showPowerLog;
    },

    _getSectionIcon: function(sectionOpened) {
        if (sectionOpened) {
            return 'expand-less'; //'arrow-drop-up';
        }
        return 'expand-more'; //'arrow-drop-down';
    },
    _getSectionTooltip: function(sectionOpened, sectionName) {
        var verb;
        if (sectionOpened) {
            verb = 'Hide';
        } else {
            verb = 'Show';
        }
        return verb + ' ' + sectionName;
    },

    _unknownVMType: function(vmType) {
        switch (vmType) {
            case 'dummy':
            case 'aws':
                return false;
            default:
                return true;
        }
    }
});
