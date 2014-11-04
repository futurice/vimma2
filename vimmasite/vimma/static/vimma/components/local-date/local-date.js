Polymer('local-date', {
    date: '',

    dateStr: 'YYYY-MM-DD',
    showDate: true,
    timeStr: 'HH:MM:SS.mmm',
    isoStr: '', // can't find a way to show this as <some-elem title=…>

    ready: function() {
        this.dateObj = new Date(this.date);
        var now = new Date();

        if (now.getFullYear() == this.dateObj.getFullYear() &&
                now.getMonth() == this.dateObj.getMonth() &&
                now.getDate() == this.dateObj.getDate()) {
            this.showDate = false;
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

        this.dateStr = [this.dateObj.getFullYear(), this.dateObj.getMonth(),
            this.dateObj.getDate()].map(fmtInt).join('-');
        this.timeStr = [this.dateObj.getHours(), this.dateObj.getMinutes(),
            this.dateObj.getSeconds()].map(fmtInt).join(':') + '.' +
                fmtMillis(this.dateObj.getMilliseconds());

        this.isoStr = this.dateObj.toISOString();
    }
});
