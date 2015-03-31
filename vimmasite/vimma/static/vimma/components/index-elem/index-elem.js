Polymer('index-elem', {
    created: function() {
        this.tabs = [
            {key: 'vms', title: 'VMs'},
            {key: 'projects', title: 'Projects'},
            {key: 'schedules', title: 'Schedules'},
            {key: 'audit', title: 'Audit (logs)'}
        ];
        this.tabs.forEach(function(t) {
            t.url = indexUrl + ajaxFragPrefix + t.key;
        });
        this.frag = getAjaxFrag();
    },

    observe: {
        '$.ajaxFrag.head': 'fragHeadChanged'
    },

    fragHeadChanged: function() {
        var i, key = this.$.ajaxFrag.head;
        for (i = 0; i < this.tabs.length; i++) {
            if (this.tabs[i].key == key) {
                return;
            }
        }
        this.async(function() {
            this.frag = this.tabs[0].key;
        });
    },

    navClicked: function(ev, detail, sender) {
        // Only run this handler if the main mouse button was pressed with no
        // modifier keys. Otherwise (e.g. middle-click; ctrl+click) bypass it.
        if (ev.button != 0 || ev.altKey || ev.ctrlKey || ev.shiftKey) {
            return;
        }
        ev.preventDefault();
        this.frag = ev.target.templateInstance.model.tab.key;
    }
});
