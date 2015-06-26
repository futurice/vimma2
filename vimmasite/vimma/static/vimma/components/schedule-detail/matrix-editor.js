Polymer({
    is: 'matrix-editor',

    properties: {
        matrix: {
            type: Array,
            notify: true
        }
    },

    _negate: function() {
        var m = clone(this.matrix), i, j;
        for (i = 0; i < m.length; i++) {
            for (j = 0; j < m[i].length; j++) {
                m[i][j] = !m[i][j];
            }
        }
        this.matrix = m;
    }
});
