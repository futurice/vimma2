Polymer({
    is: 'index-elem',

    properties: {
        _frag: String,
        _fragHead: {
            type: String,
            observer: 'fragHeadChanged'
        },
        _tabs: {
            type: Object,
            readOnly: true,
            value: function() {
                return [
                    {key: 'vms', title: 'VMs'},
                    {key: 'projects', title: 'Projects'},
                    {key: 'schedules', title: 'Schedules'},
                    {key: 'audit', title: 'Audit (logs)'}
                ];
            },
        },
        _selected: {
            type: Number,
            observer: 'selectedChanged'
        }
    },

    fragHeadChanged: function(newV, oldV) {
        var i;
        for (i = 0; i < this._tabs.length; i++) {
            if (this._tabs[i].key == newV) {
                break;
            }
        }

        if (i == this._tabs.length) {
            this._frag = this._tabs[0].key;
            return;
        }
        this._selected = i;
    },

    selectedChanged: function(newV, oldV) {
        var newHead = this._tabs[newV].key;
        /* If navigating in the browser, the fragment has already changed (with
         * a possible /tail too). Don't touch it. If clicking a tab, overwrite
         * the entire fragment (not just its ‘head’ part).
         */
        if (this._fragHead != newHead) {
            this._frag = newHead;
        }
    },

    _equal: function(a, b) {
        return a === b;
    }
});
