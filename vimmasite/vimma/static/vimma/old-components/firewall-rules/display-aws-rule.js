Polymer('display-aws-rule', {
    loading: true,
    loadingSucceeded: false,

    ruleid: null,

    aws_fw_rule: null,


    ready: function() {
        this.reload();
    },
    reload: function() {
        this.$.ajax.fire('start');

        this.loading = true;

        this.aws_fw_rule = null;

        this.loadAwsRule();
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

	loadAwsRule: function() {
        var ok = (function(resultArr) {
            this.aws_fw_rule = resultArr[0].results[0];
            if (!this.aws_fw_rule) {
            	this.loadFail();
            	return;
            }
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiAWSFirewallRuleList + '?firewallrule=' + this.ruleid],
                ok, this.loadFail.bind(this));
    }
});
