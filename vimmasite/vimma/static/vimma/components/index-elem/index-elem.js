Polymer('index-elem', {
    created: function() {
        this.tabs = [
            {key: 'vms', title: 'VMs'},
            {key: 'projects', title: 'Projects'},
            {key: 'schedules', title: 'Schedules'},
            {key: 'audit', title: 'Audit (logs)'}
        ];
        this.frag = getAjaxFrag();
    },

    domIsReady: false,
    domReady: function() {
        this.domIsReady = true;
        this.updateSelectedIdx();
    },

    observe: {
        '$.ajaxFrag.head': 'updateSelectedIdx'
    },

    updateSelectedIdx: function() {
        if (!this.domIsReady) {
            return;
        }
        var i, key = this.$.ajaxFrag.head;
        for (i = 0; i < this.tabs.length; i++) {
            if (this.tabs[i].key == key) {
                this.selectedIdx = i;
                return;
            }
        }
        this.frag = this.tabs[0].key;
    },

    selectedIdxChanged: function() {
        var key = this.tabs[this.selectedIdx].key;
        // Don't overwrite the entire fragment on page load if the tab
        // doesn't change (i.e. don't replace "vms/3" with "vms").
        if (this.$.ajaxFrag.head != key) {
            this.frag = key;
        }
    }
});
