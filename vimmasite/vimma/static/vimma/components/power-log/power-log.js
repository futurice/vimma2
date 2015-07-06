Polymer({
    is: 'power-log',

    properties: {
        vmid: {
            type: String,
            observer: '_vmidChanged'
        },

        _showOnlyTransitions: {
            type: Boolean,
            value: false
        },

        _url: {
            type: String,
            observer: '_urlChanged'
        },

        _loadingToken: Object,  /* same logic as in <vm-list> */
        _loading: Boolean,
        _error: String, // empty string if no error
        _apiData: Object,
        _chartData: {
            type: Object,
            computed: '_computeChartData(_apiData, _showOnlyTransitions)',
            observer: '_chartDataChanged'
        }
    },

    _vmidChanged: function(newV, oldV) {
        this._reload();
    },

    _reload: function() {
        this._url = null;
        this._url =  vimmaApiPowerLogList +
            '?vm=' + encodeURIComponent(this.vmid);
    },

    _urlChanged: function(newV, oldV) {
        if (!newV) {
            return;
        }

        var token = {};
        this._loadingToken = token;
        this._loading = true;
        this._error = '';

        var success = (function(resArr) {
            if (this._loadingToken != token) {
                return;
            }

            this._apiData = resArr[0];
            this._error = '';
            this._loading = false;
        }).bind(this);

        var fail = (function(err) {
            if (this._loadingToken != token) {
                return;
            }

            this._error = err;
            this._loading = false;
        }).bind(this);

        apiGet([newV], success, fail);
    },

    _computeChartData: function(apiData, showOnlyTransitions) {
        var dataPoints = [];
        apiData.results.forEach(function(pl) {
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

    _chartDataChanged: function(newV, oldV) {
        this._drawChart();
    },

    _drawChart: function() {
        $(this.$.container).highcharts({
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
                data: this._chartData
            }],
            plotOptions: {
                series: {
                    animation: false
                }
            }
        });
    },

    _loadOlder: function() {
        this._url = this._apiData.next;
    },
    _loadNewer: function() {
        this._url = this._apiData.previous;
    }
});
