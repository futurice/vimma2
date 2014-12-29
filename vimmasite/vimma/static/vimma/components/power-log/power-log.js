Polymer('power-log', {
    loading: true,
    loadingSucceeded: false,

    powerLogs: null,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');
        this.loading = true;

        this.powerLogs = null;

        this.loadPowerLogs();
    },
    loadFail: function(errorText) {
        this.$.ajax.fire('end', {success: false, errorText: errorText});

        this.loading = false;
        this.loadingSucceeded = false;
    },
    loadSuccess: function() {
        this.$.ajax.fire('end', {success: true});

        this.loading = false;
        this.loadingSucceeded = true;
    },

    loadPowerLogs: function() {
        var ok = (function(resultArr) {
            this.powerLogs = resultArr[0].results;
            this.async(this.drawChart);
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiPowerLogList + '?vm=' + this.vmid],
                ok, this.loadFail.bind(this));
    },

    drawChart: function() {
        var dataPoints = [];
        this.powerLogs.forEach(function(pl) {
            var x = new Date(pl.timestamp).valueOf(),
                y = pl.powered_on ? 1 : 0;
            dataPoints.push([x, y]);
        });
        dataPoints.reverse();

        $(this.shadowRoot.getElementById('container')).highcharts({
            title: {
                text: ''
            },
            chart: {
                type: 'area'
            },
            xAxis: {
                title: {
                    text: 'Date & Time'
                },
                type: 'datetime'
            },
            yAxis: {
                title: {
                    text: 'Power'
                },
                min: 0,
                max: 1
            },
            series: [{
                name: 'Power',
                showInLegend: false,
                data: dataPoints
            }]
        });
    }
});
