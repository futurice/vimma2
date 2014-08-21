Polymer('error-display', {
    text: '',
    size: 50,

    ready: function() {
        this.size = Math.max(this.size, 1);
        this.needsTrimming = this.text.length > this.size;
        if (this.needsTrimming) {
            this.collapsed = true;
            this.trimmedText = this.text.substr(0, this.size - 1) + '…';
        }
    },

    toggle: function() {
        if (this.needsTrimming) {
            this.collapsed = !this.collapsed;
        }
    }
});
