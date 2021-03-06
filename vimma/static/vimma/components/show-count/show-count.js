Polymer({
    is: 'show-count',
    properties: {
        n: Number,
        one: String,
        many: {
            type: String,
            value: null
        },

        _result: {
            type: String,
            computed: '_makeResult(n, one, many)'
        }
    },

    _makeResult: function(n, one, many) {
        var what;
        if (n === 1) {
            what = one;
        } else if (many !== null) {
            what = many;
        } else {
            what = one + 's';
        }

        return n + ' ' + what;
    }
});
