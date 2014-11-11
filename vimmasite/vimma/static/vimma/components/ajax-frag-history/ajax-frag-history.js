Polymer('ajax-frag-history', {
	frag: '',

	// Don't push an entry to browser history stack
	_ignoreFragUpdate: false,

	ready: function() {
		window.addEventListener("hashchange", this.navigate.bind(this));
	},

	navigate: function() {
		// don't push a history entry
		this._ignoreFragUpdate = true;
		this.frag = getAjaxFrag();
	},

	fragChanged: function() {
		if (this._ignoreFragUpdate) {
			this._ignoreFragUpdate = false;
			return;
		}

		// doesn't trigger 'hashchange' event listeners
		setAjaxFrag(this.frag);
	}
});