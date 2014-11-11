Polymer('index-elem', {
    created: function() {
        this.tabs = [
            {key: 'vms', title: 'VMs'},
            {key: 'projects', title: 'Projects'},
            {key: 'schedules', title: 'Schedules'},
            {key: 'audit', title: 'Audit (logs)'}
        ];
    },
    domReady: function() {
        this.$.ajaxFrag.frag = getAjaxFrag();
        this.async(this.updateSelectedIdx);
    },

    observe: {
        '$.ajaxFrag.head': 'updateSelectedIdx'
    },

    updateSelectedIdx: function() {
        var i, key = this.$.ajaxFrag.head;
        for (i = 0; i < this.tabs.length; i++) {
            if (this.tabs[i].key == key) {
                this.selectedIdx = i;
                return;
            }
        }
        this.$.ajaxFrag.frag = this.tabs[0].key;
    },

    selectedIdxChanged: function() {
        var key = this.tabs[this.selectedIdx].key;
        // Don't overwrite the entire fragment on page load if the tab
        // doesn't change (i.e. don't replace "vms/3" with "vms").
        if (this.$.ajaxFrag.head != key) {
            this.$.ajaxFrag.frag = key;
        }
    }
});
