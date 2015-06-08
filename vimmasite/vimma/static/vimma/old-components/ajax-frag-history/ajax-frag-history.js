Polymer('ajax-frag-history', {
    frag: '',

    // On next change, don't push an entry to the browser history stack
    _ignoreNextUpdate: false,

    domIsReady: false,
    domReady: function() {
        window.addEventListener("hashchange", this.navigate.bind(this));

        // When creating <ajax-frag-history frag="abc"></ajax-frag-history>:
        // ― ready() runs
        // ― fragChanged() runs (with frag="abc")
        // ― domReady() runs
        // Don't push a history item if the inital url was #!abc. So ignore
        // frag changes until domReady.
        this.domIsReady = true;
    },

    navigate: function() {
        this._ignoreNextUpdate = true;
        this.frag = getAjaxFrag();
    },

    fragChanged: function() {
        if (!this.domIsReady) {
            return;
        }
        if (this._ignoreNextUpdate) {
            this._ignoreNextUpdate = false;
            return;
        }

        // doesn't trigger 'hashchange' event listeners
        setAjaxFrag(this.frag);
    }
});
