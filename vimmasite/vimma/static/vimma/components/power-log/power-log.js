Polymer('power-log', {
    vmid: -1,
    showOnlyTransitions: false,
    // the results as they came from the API
    apiPage: null,

    computed: {
        // for HighCharts series.data
        chartData: 'computeChartData(apiPage, showOnlyTransitions)'
    },

    chartDataChanged: function() {
        this.drawChart();
    },

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.$.ajax.fire('start');
        this.apiPage = null;
        this.loadAPIPage(this.getAPIStartURL());
    },
    loadFail: function(errorText) {
        this.$.ajax.fire('end', {success: false, errorText: errorText});
    },
    loadSuccess: function() {
        this.$.ajax.fire('end', {success: true});
    },

    getAPIStartURL: function() {
        return vimmaApiPowerLogList + '?vm=' + encodeURIComponent(this.vmid);
    },

    loadAPIPage: function(url) {
        var ok = (function(resultArr) {
            this.apiPage = resultArr[0];
            this.loadSuccess();
        }).bind(this);
        apiGet([url], ok, this.loadFail.bind(this));
    },
    loadOlder: function() {
        this.$.ajax.fire('start');
        this.loadAPIPage(this.apiPage.next);
    },
    loadNewer: function() {
        this.$.ajax.fire('start');
        this.loadAPIPage(this.apiPage.previous);
    },

    computeChartData: function(apiPage, showOnlyTransitions) {
        if (apiPage == null) {
            return null;
        }

        var dataPoints = [];
        apiPage.results.forEach(function(pl) {
            var x = new Date(pl.timestamp).valueOf(),
                y = pl.powered_on ? 1 : 0;
            dataPoints.push([x, y]);
        });

        if (showOnlyTransitions) {
            dataPoints = (function() {
                // remove a data point if it has the same y value as both its
                // left and right neighbours.
                var idxToRemove = {}, i, crtV, leftV, rightV;
                for (i = 1; i < dataPoints.length - 1; i++) {
                    crtV = dataPoints[i][1];
                    leftV = dataPoints[i-1][1];
                    rightV = dataPoints[i+1][1];
                    if (crtV == leftV && crtV == rightV) {
                        idxToRemove[i] = null;
                    }
                }

                var result = [];
                for (i = 0; i < dataPoints.length; i++) {
                    if (!(i in idxToRemove)) {
                        result.push(dataPoints[i]);
                    }
                }
                return result;
            })();
        }

        return dataPoints.reverse();
    },

    drawChart: function() {
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
                data: this.chartData
            }],
            plotOptions: {
                series: {
                    animation: false
                }
            }
        });
    }
});
