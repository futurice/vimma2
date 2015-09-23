Polymer({
    is: 'vm-detail',

    behaviors: [VimmaBehaviors.Equal],

    ready: function() {
      this.fire('vm-detail-created', {});
    },

    vmUrl: function(name, vmid) {
      return url(name+'vm-detail', [vmid]);
    },

    properties: {
        vmid: {
            type: Number,
            observer: '_vmidChanged'
        },

        vm: Object,

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
      if(this.vm.expiration) {
        return this.vm.expiration.expires_at;
      }
      return null;
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
        // TODO: vm/destroy
    },

    _reboot: function(ev) {
        ev.stopPropagation();
        if (!confirm('Reboot VM: ‘' + this.getName() + '’?')) {
            return;
        }
        // TODO: vm/reboot
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
    }
});
