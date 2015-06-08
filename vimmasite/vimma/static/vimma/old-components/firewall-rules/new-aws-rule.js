Polymer('new-aws-rule', {
	data: null,

	awsFirewallRuleProtocolChoices: awsFirewallRuleProtocolChoices,

	ready: function() {
		this.data = {
			ip_protocol: awsFirewallRuleProtocolChoices[0].value,
			from_port: 80,
			to_port: 80,
			cidr_ip: '0.0.0.0/32'
		};
	},

	observe: {
		'data.from_port': 'parseFromPort',
		'data.to_port': 'parseToPort'
	},

	parseFromPort: function() {
		this.data.from_port = Number.parseInt('' + this.data.from_port);
	},
	parseToPort: function() {
		this.data.to_port = Number.parseInt('' + this.data.to_port);
	},

	protoChanged: function(ev) {
		this.data.ip_protocol = awsFirewallRuleProtocolChoices[ev.target.selectedIndex].value;
	}
});
