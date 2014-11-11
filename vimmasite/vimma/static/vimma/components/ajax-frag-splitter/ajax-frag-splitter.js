Polymer('ajax-frag-splitter', {
	frag: '',
	created: function() {
		// ensure the .head and .tail fields exist
		this.splitFrag();
	},

	splitFrag: function() {
		this.head = ajaxFragHead(this.frag);
		this.tail = ajaxFragTail(this.frag);
	},
	joinFrag: function() {
		this.frag = ajaxFragJoin(this.head, this.tail);
	},

	observe: {
		frag: 'splitFrag',
		head: 'joinFrag',
		tail: 'joinFrag'
	}
});
