(function() {
    var orderNameAsc='+name', orderNameDesc='-name',
        orderStateAsc='+state', orderStateDesc='-state',
        orderProjectAsc='+project', orderProjectDesc='-project',
        orderExpiryAsc='+expiry', orderExpiryDesc='-expiry';

    var compareFuncs = {};
    compareFuncs[orderNameAsc] = compareNameAsc;
    compareFuncs[orderNameDesc] = compareNameDesc;

    compareFuncs[orderStateAsc] = compareStateAsc;
    compareFuncs[orderStateDesc] = compareStateDesc;

    compareFuncs[orderProjectAsc] = compareProjectAsc;
    compareFuncs[orderProjectDesc] = compareProjectDesc;

    compareFuncs[orderExpiryAsc] = compareExpiryAsc;
    compareFuncs[orderExpiryDesc] = compareExpiryDesc;

    function compare(a, b) {
        if (a < b) {
            return -1;
        }
        if (a > b) {
            return 1;
        }
        return 0;
    }

    function compareNameAsc(a, b) {
        a = a.getName().toLowerCase();
        b = b.getName().toLowerCase();
        return compare(a, b);
    }
    function compareNameDesc(a, b) {
        return compareNameAsc(b, a);
    }

    function compareStateAsc(a, b) {
        // destroyed, off, on
        if (a.isDestroyed() != b.isDestroyed()) {
            return compare(b.isDestroyed(), a.isDestroyed());
        }
        if (a.isDestroyed()) {
            return 0;
        }
        return compare(a.isOn(), b.isOn());
    }
    function compareStateDesc(a, b) {
        return compareStateAsc(b, a);
    }

    function compareProjectAsc(a, b) {
        a = a.getProjectName().toLowerCase();
        b = b.getProjectName().toLowerCase();
        return compare(a, b);
    }
    function compareProjectDesc(a, b) {
        return compareProjectAsc(b, a);
    }

    function compareExpiryAsc(a, b) {
        a = new Date(a.getExpiryDate()).valueOf();
        b = new Date(b.getExpiryDate()).valueOf();
        return compare(a, b);
    }
    function compareExpiryDesc(a, b) {
        return compareExpiryAsc(b, a);
    }

    Polymer({
        is: 'vm-list',

        behaviors: [VimmaBehaviors.Equal],

        properties: {
            frag: {
                type: String,
                notify: true
            },
            _fragHead: String,

            // load destroyed or non-destroyed VMs
            destroyed: {
                type: Boolean,
                value: false,
                observer: '_destroyedChanged'
            },

            expanded: {
                type: Boolean,
                value: false
            },

            // avoid 3 nested ‘dom-if’s
            _showList: {
                type: Boolean,
                computed: '_computeShowList(_loading, _error, expanded)'
            },

            _headingIcon: {
                type: String,
                computed: '_computeHeadingIcon(expanded)'
            },

            /* Every ‘reload’ operation sets this token to a new object. When
             * it completes (with either error or success) it does nothing if
             * this token has changed. This way only the ‘reload’ operation
             * started last applies its result, regardles of the order in which
             * the ‘reload’ operations finish.
             */
            _loadingToken: Object,
            _loading: Boolean,
            _error: String, // empty string if no error
            _vms: Array,    // all the VM models, in arbitrary order

            _order: {
                type: String,
                value: orderNameAsc
            },

            _nameSortIcon: {
                type: String,
                computed: '_computeNameSortIcon(_order)'
            },
            _stateSortIcon: {
                type: String,
                computed: '_computeStateSortIcon(_order)'
            },
            _projectSortIcon: {
                type: String,
                computed: '_computeProjectSortIcon(_order)'
            },
            _expirySortIcon: {
                type: String,
                computed: '_computeExpirySortIcon(_order)'
            },

            _nameClass: {
                type: String,
                computed: '_computeNameClass(_order)'
            },
            _stateClass: {
                type: String,
                computed: '_computeStateClass(_order)'
            },
            _projectClass: {
                type: String,
                computed: '_computeProjectClass(_order)'
            },
            _expiryClass: {
                type: String,
                computed: '_computeExpiryClass(_order)'
            },

            _sortedVms: {
                type: Array,
                computed: '_sort(_vms, _order)'
            }
        },

        observers: [
            '_expandIfVMSelected(_vms, _fragHead)'
        ],

        ready: function() {
            this.reload();
        },

        reload: function() {
            var token = {};
            this._loadingToken = token;
            this._loading = true;

            var success = (function(vms) {
                if (this._loadingToken != token) {
                    return;
                }

                this._vms = vms;
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

            this.$.vdm.loadAllVMs(this.destroyed, success, fail);
        },

        _destroyedChanged: function(newV, oldV) {
            this.reload();
        },

        _toggle: function() {
            this.expanded = !this.expanded;
        },

        _computeShowList: function(loading, error, expanded) {
            return !loading && !error && expanded;
        },

        _computeHeadingIcon: function(expanded) {
            if (expanded) {
                return 'expand-less';
            }
            return 'expand-more';
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
        _isDestroyed: function(vm) {
            return vm.isDestroyed();
        },

        _sort: function(vms, order) {
            return vms.slice().sort(compareFuncs[order]);
        },
        _toggleOrder: function(default_, alternate) {
            if (this._order == default_) {
                this._order = alternate;
            } else {
                this._order = default_;
            }
        },
        _sortByName: function() {
            this._toggleOrder(orderNameAsc, orderNameDesc);
        },
        _sortByState: function() {
            this._toggleOrder(orderStateDesc, orderStateAsc);
        },
        _sortByProject: function() {
            this._toggleOrder(orderProjectAsc, orderProjectDesc);
        },
        _sortByExpiry: function() {
            this._toggleOrder(orderExpiryAsc, orderExpiryDesc);
        },

        // arrow-drop-up if order if ascOrder, -down if descOrder, else ''.
        _computeSortIcon: function(order, ascOrder, descOrder) {
            if (order == ascOrder) {
                return 'arrow-drop-up';
            }
            if (order == descOrder) {
                return 'arrow-drop-down';
            }
            return '';
        },
        _computeNameSortIcon: function(order) {
            return this._computeSortIcon(order, orderNameAsc, orderNameDesc);
        },
        _computeStateSortIcon: function(order) {
            return this._computeSortIcon(order, orderStateAsc, orderStateDesc);
        },
        _computeProjectSortIcon: function(order) {
            return this._computeSortIcon(order,
                    orderProjectAsc, orderProjectDesc);
        },
        _computeExpirySortIcon: function(order) {
            return this._computeSortIcon(order,
                    orderExpiryAsc, orderExpiryDesc);
        },


        _computeClass: function(order, selectedOrders) {
            var i, n = selectedOrders.length;
            for (i = 0; i < n; i++) {
                if (order == selectedOrders[i]) {
                    return 'ordering-selected';
                }
            }
            return '';
        },
        _computeNameClass: function(order) {
            return this._computeClass(order, [orderNameAsc, orderNameDesc]);
        },
        _computeStateClass: function(order) {
            return this._computeClass(order, [orderStateAsc, orderStateDesc]);
        },
        _computeProjectClass: function(order) {
            return this._computeClass(order,
                    [orderProjectAsc, orderProjectDesc]);
        },
        _computeExpiryClass: function(order) {
            return this._computeClass(order, [orderExpiryAsc, orderExpiryDesc]);
        },

        _vmExpanded: function(ev) {
            this.frag = ev.detail + '';
        },
        _vmCollapsed: function(ev) {
            if (this._fragHead == ev.detail) {
                this.frag = '';
            }
        },

        _expandIfVMSelected: function(_vms, _fragHead) {
            _vms.forEach(function(vm) {
                if (vm.vm.id == _fragHead) {
                    this.expanded = true;
                }
            }, this);
        }
    });
})();
