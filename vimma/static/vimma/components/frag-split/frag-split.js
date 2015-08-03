(function() {
    var fu = document.createElement('frag-util');

    Polymer({
        is: 'frag-split',

        properties: {
            frag: {
                type: String,
                notify: true,
                observer: 'split'
            },
            head: {
                type: String,
                notify: true,
                observer: 'merge'
            },
            tail: {
                type: String,
                notify: true,
                observer: 'merge'
            }
        },

        ready: function() {
            // Default values interfere with user-provided ones (because of the
            // cyclic computations via observers):
            // <frag-split frag="b/c">
            // If the default value for ‘tail’ is set after the user-provided
            // ‘frag’, the result is: head="b" tail="" frag="b".

            // Don't use default property values. Use ‘ready’ instead.
            // Order matters: set ‘frag’ last, otherwise
            // <ajax-split head="a"> will be replaced with an empty ‘frag’.
            if (this.head === undefined) {
                this.head = '';
            }
            if (this.tail === undefined) {
                this.tail = '';
            }
            if (this.frag === undefined) {
                this.frag = '';
            }
        },

        split: function() {
            if (this.frag === undefined) {
                return;
            }
            // prevent overwriting frag until we update *both* head and tail
            this.tail = undefined;

            this.head = fu.fragHead(this.frag);
            this.tail = fu.fragTail(this.frag);
        },

        merge: function() {
            if (this.head === undefined || this.tail === undefined) {
                return;
            }
            this.frag = fu.fragJoin(this.head, this.tail);
        }
    });
})();
