Polymer({
    is: 'vm-detail',

    behaviors: [VimmaBehaviors.Equal],

    ready: function() {
      this.fire('vm-detail-created', {});
    },

    _vmUrl: function(vmid) {
      return '/api/dummyvms/'+vmid+'/';
    },

    properties: {
        vmid: {
            type: Number,
            observer: '_vmidChanged'
        },

        _loadingToken: Object,  /* same logic as in <vm-list> */
        _loading: Boolean,
        _error: String, // empty string if no error
        vm: Object,    // the VM data model

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

    _reload: function() {
    },

    _getShowHideIcon: function(expanded) {
        if (expanded) {
            return 'expand-less';
        }
        return 'expand-more';
    },

    getExpiryDate: function() {
        return this.vm.expiration.expires_at || null;
    },
    _getExpiryClass: function(vm) {
        var d = new Date(this.getExpiryDate()).valueOf(),
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
    getName: function(vm) {
      return this.vm.name;
    },
    _getProjectName: function() {
        return this.vm.project.name;
    },
    _getStateName: function() {
        if (this.vm.destroyed_at !== null) {
            return 'Destroyed';
        }
        if (this.vm.isOn) {
            return 'Powered ON';
        }
        return 'Powered OFF';
    },
    _getStateIcon: function() {
        if (this.vm.destroyed_at !== null) {
            return 'delete';
        }
        if (this.vm.isOn) {
            return 'check-circle';
        }
        return 'remove-circle';
    },
    _getStateClass: function() {
        if (this.vm.destroyed_at !== null) {
            return 'destroyed';
        }
        if (this.vm.isOn) {
            return 'powered-on';
        }
        return 'powered-off';
    },

    _destroy: function(ev) {
        ev.stopPropagation();
        if (!confirm('Destroy VM: ‘' + this.getName() + '’?')) {
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
        if (!confirm('Reboot VM: ‘' + this.getName() + '’?')) {
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
