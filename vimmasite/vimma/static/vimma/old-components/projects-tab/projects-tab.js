Polymer('projects-tab', {
    observe: {
        '$.ajaxFrag.head': 'fragHeadChanged'
    },

    frag: '',   // AJAX URL fragment
    fragHeadChanged: function() {
        var s = this.$.ajaxFrag.head, i = parseInt(s, 10);
        if (i + '' != s) {
            i = null;
            if (this.prjId == null) {
                // ensure the changed watcher runs and deletes the invalid frag
                this.async(this.prjIdChanged);
            }
        }
        this.prjId = i;
    },

    prjId: null,
    prjIdChanged: function() {
        var head = '';
        if (this.prjId != null) {
            head = '' + this.prjId;
        }
        if (head != this.$.ajaxFrag.head) {
            this.frag = head;
        }
    },

    projectSelected: function(e, detail, sender) {
        e.stopPropagation();
        this.prjId = e.detail.id;
    },
    unselectProject: function() {
        this.prjId = null;
    }
});
