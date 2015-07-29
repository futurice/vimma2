(function() {
    function padInt(n, len) {
        if (n < 0) {
            console.warn("Padding negative number:", n);
        }
        var s = n + '';
        // O(len^2), but OK for our use-case: len ≤ 3
        while (s.length < len) {
            s = 0 + s;
        }
        return s;
    }

    Polymer({
        is: 'local-date',

        properties: {
            epochMillis: {
                type: Number,
                value: null
            },
            dateString: {
                type: String,
                value: null
            },
            hideMillis: {
                type: Boolean,
                value: false
            },
            _date: {
                type: Date,
                computed: '_computeDate(epochMillis, dateString)'
            },
            local: {
                type: String,
                computed: '_computeLocal(_date, hideMillis)'
            },
            iso: {
                type: String,
                computed: '_computeIso(_date)'
            }
        },

        _computeDate: function(epochMillis, dateString) {
            var val = 0;
            if (epochMillis !== null) {
                val = epochMillis;
            } else if (dateString !== null) {
                val = dateString;
            }
            return new Date(val);
        },

        _computeLocal: function(date, hideMillis) {
            var dateStr = [date.getFullYear(), date.getMonth() + 1,
                date.getDate()].map(function(n) {
                    return padInt(n, 2);
                }).join('-');

            var timeStr = [date.getHours(), date.getMinutes(),
                date.getSeconds()].map(function(n) {
                    return padInt(n, 2);
                }).join(':');

            if (!hideMillis) {
                timeStr += '.' + padInt(date.getMilliseconds(), 3);
            }

            return dateStr + ' ' + timeStr;
        },

        _computeIso: function(date) {
            return date.toISOString();
        }
    });
})();
