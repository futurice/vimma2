Polymer({
    is: 'vm-detail',

    properties: {
        vmid: {
            type: Number,
            observer: '_vmidChanged'
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
            value: false
        }
    },

    _vmidChanged: function(newV, oldV) {
        this._expanded = this.properties._expanded.value;
        this._reload();
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

    /* Call VMModel methods (we can't do it in the template directly). */
    _getExpiryDate: function(vm) {
        return vm.getExpiryDate();
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

    _toggle: function() {
        this._expanded = !this._expanded;
    }
});
