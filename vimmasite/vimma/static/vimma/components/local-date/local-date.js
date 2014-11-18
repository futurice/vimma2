Polymer('local-date', {
    date: '',
    alwaysshowdate: false,

    result: 'YYYY-MM-DD HH:MM:SS.mmm',
    isoStr: '', // can't find a way to show this as <some-elem title=…>

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

        var dateStr = [dateObj.getFullYear(), dateObj.getMonth(),
            dateObj.getDate()].map(fmtInt).join('-');
        var timeStr = [dateObj.getHours(), dateObj.getMinutes(),
            dateObj.getSeconds()].map(fmtInt).join(':') + '.' +
                fmtMillis(dateObj.getMilliseconds());

        this.result = showDate ? dateStr + ' ' + timeStr : timeStr;
    }
});
