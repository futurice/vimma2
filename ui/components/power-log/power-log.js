Polymer({
    is: 'power-log',

    properties: {
        vm: {
            type: Object,
            observer: 'vmChanged'
        },

        _showOnlyTransitions: {
            type: Boolean,
            value: false
        },

        _chartData: {
            type: Object,
            computed: '_computeChartData(powerlogs, _showOnlyTransitions)',
            observer: '_chartDataChanged'
        }
    },

    vmChanged: function(newV, oldV) {
        this.reload();
    },

    reload: function() {
        this.powerUrl = vmurl(this.vm, 'powerlog-list', {vm: this.vm.id});
        this.$.powerlogajax.generateRequest();
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
        this.powerUrl = this.powerlogs.next;
        this.$.powerlogajax.generateRequest();
    },
    _loadNewer: function() {
        this.powerUrl = this.powerlogs.previous;
        this.$.powerlogajax.generateRequest();
    }
});
