Polymer({
    is: 'frag-history',

    properties: {
        frag: {
            type: String,
            notify: true,
            observer: 'fragChanged'
        }
    },

    created: function() {
        // store the listener so we can remove it when detaching
        this.listener = this.hashchangeListener.bind(this);
    },

    ready: function() {
        if (typeof(this.frag) !== 'string') {
            this.listener();
        }
    },

    attached: function() {
        window.addEventListener('hashchange', this.listener);
    },

    detached: function() {
        window.removeEventListener('hashchange', this.listener);
    },

    hashchangeListener: function() {
        this.frag = this.$.fu.getFrag();
    },

    fragChanged: function() {
        if (this.$.fu.getFrag() != this.frag) {
            // Only add a history entry if the URL hash != ‘frag’.
            // When creating <frag-history frag="abc"></frag-history>, ‘frag’
            // is set to ‘abc’ during the creation lifecycle.
            // Don't add a history entry if the URL hash is aready ‘frag’.
            this.$.fu.setFrag(this.frag);
        }
    }
});
