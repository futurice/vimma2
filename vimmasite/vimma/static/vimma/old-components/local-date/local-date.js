Polymer('local-date', {
    date: '',
    alwaysshowdate: false,
    hidemillis: false,

    result: 'YYYY-MM-DD HH:MM:SS.mmm',
    isoStr: '',

    ready: function() {
        var dateObj = new Date(this.date);
        this.isoStr = dateObj.toISOString();
        var now = new Date();

        var showDate = true;
        if (!this.alwaysshowdate &&
                now.getFullYear() == dateObj.getFullYear() &&
                now.getMonth() == dateObj.getMonth() &&
                now.getDate() == dateObj.getDate()) {
            showDate = false;
        }

        function fmtInt(i) {
            var s = i + '';
            if (s.length == 1) {
                s = '0' + s;
            }
            return s;
        }

        function fmtMillis(i) {
            var s = i + '';
            if (s.length > 3) {
                throw 'Invalid millisecond count: ' + s;
            }
            while (s.length < 3) {
                s = '0' + s;
            }
            return s;
        }

        var dateStr = [dateObj.getFullYear(), dateObj.getMonth() + 1,
            dateObj.getDate()].map(fmtInt).join('-');
        var timeStr = [dateObj.getHours(), dateObj.getMinutes(),
            dateObj.getSeconds()].map(fmtInt).join(':');
        if (!this.hidemillis) {
            timeStr += '.' + fmtMillis(dateObj.getMilliseconds());
        }

        this.result = showDate ? dateStr + ' ' + timeStr : timeStr;
    }
});
