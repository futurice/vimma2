(function() {
    /* Load all  firewall rule models and call successCallback(model-array)
     * or errCallback(errorText).
     */
    function loadModels(vmid, successCallback, errCallback) {
        var url = vimmaApiFirewallRuleList + '?vm=' + vmid;
        apiGetAll([url], loadStep2, errCallback);

        function loadStep2(resArr) {
            var fw_rules = resArr[0];
            var urls = [];
            fw_rules.forEach(function(fwr) {
                urls.push(vimmaApiFirewallRuleList +
                        '?firewallrule=' + fwr.id);
                urls.push(vimmaApiFirewallRuleExpirationList +
                        '?firewallrule=' + fwr.id);
            });

            apiGetAll(urls, makeModels, errCallback);

            function makeModels(resArr) {
                var i = 0, models = [];
                for (i = 0; i < fw_rules.length; i++) {
                    models.push({
                        fw_rule: fw_rules[i],
                        aws_fw_rule: resArr[i*2][0],
                        fw_rule_exp: resArr[i*2+1][0]
                    });
                }
                successCallback(models);
            }
        }
    }

    Polymer({
        is: 'aws-firewall-rules',

        properties: {
            vmid: {
                type: Number,
                observer: '_vmidChanged'
            },

            _loadingToken: Object,
            _loading: Boolean,
            _loadErr: String,
            _models: Array,

            _deleteInFlight: Boolean,
            _deleteErr: String
        },

        _vmidChanged: function(newV, oldV) {
            this._reload();
        },

        _reload: function() {
            var token = {};
            this._loadingToken = token;
            this._loading = true;

            this._deleteErr = '';

            var ok = (function(models) {
                if (this._loadingToken != token) {
                    return;
                }

                this._models = models;
                this._loadErr = '';
                this._loading = false;
            }).bind(this);

            var fail = (function(errorText) {
                if (this._loadingToken != token) {
                    return;
                }

                this._loadErr = errorText;
                this._loading = false;
            }).bind(this);

            loadModels(this.vmid, ok, fail);
        },

        _getPortDisplay: function(model) {
            var a = model.aws_fw_rule.from_port, b = model.aws_fw_rule.to_port;
            if (a === b) {
                return a;
            }
            return a + '–' + b;
        },

        _delete: function(ev) {
            this._deleteInFlight = true;

            $.ajax({
                url: vimmaEndpointDeleteFirewallRule,
                type: 'POST',
                contentType: 'application/json; charset=UTF-8',
                headers: {
                    'X-CSRFToken': $.cookie('csrftoken')
                },
                data: JSON.stringify({
                    id: ev.model.item.fw_rule.id
                }),
                complete: (function() {
                    this._deleteInFlight = false;
                }).bind(this),
                success: (function(data) {
                    this._reload();
                }).bind(this),
                error: (function() {
                    var errorText = getAjaxErr.apply(this, arguments);
                    this._deleteErr = errorText;
                }).bind(this)
            });
        }
    });
})();
