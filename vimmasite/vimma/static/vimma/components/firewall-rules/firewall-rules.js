Polymer('firewall-rules', {
    loading: true,
    loadingSucceeded: false,

    vmid: null,

    vm: null,
    vmProvider: null,
    firewallRules: null,

    showComposer: false,
    newRuleData: null,

    ready: function() {
        this.reload();
    },
    reload: function() {
        this.$.ajax.fire('start');

        this.loading = true;

        this.vm = null;
        this.vmProvider = null;
        this.firewallRules = null;

        this.showComposer = false;

        this.loadVM();
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

    loadVM: function() {
        var ok = (function(resultArr) {
            this.vm = resultArr[0];
            this.loadVMProviderAndFwRules();
        }).bind(this);
        apiGet([vimmaApiVMDetailRoot + this.vmid + '/'],
                ok, this.loadFail.bind(this));
    },
    loadVMProviderAndFwRules: function() {
        var ok = (function(resultArr) {
            this.vmProvider = resultArr[0];
            this.firewallRules = resultArr[1].results;
            this.loadFwRuleExpirationItems();
        }).bind(this);
        apiGet([vimmaApiProviderDetailRoot + this.vm.provider + '/',
                vimmaApiFirewallRuleList + '?vm=' + this.vmid],
                ok, this.loadFail.bind(this));
    },
    loadFwRuleExpirationItems: function() {
        var ok = (function(resultArr) {
            resultArr.forEach((function(x, i) {
                this.firewallRules[i].extra_expiration = x.results[0].expiration;
            }).bind(this));
            this.loadSuccess();
        }).bind(this);
        var urls = [];
        this.firewallRules.forEach(function(r) {
            urls.push(vimmaApiFirewallRuleExpirationList + '?firewallrule=' + r.id);
        });
        apiGet(urls, ok, this.loadFail.bind(this));
    },

    toggleComposer: function() {
        this.showComposer = !this.showComposer;
    },

    createRule: function() {
        this.$.ajax.fire('start');

        $.ajax({
            url: vimmaEndpointCreateFirewallRule,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                vmid: this.vmid,
                data: this.newRuleData
            }),
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
                this.reload();
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    },

    deleteRule: function(ev) {
        this.$.ajax.fire('start');

        $.ajax({
            url: vimmaEndpointDeleteFirewallRule,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                id: ev.target.templateInstance.model.id
            }),
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
                this.reload();
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    }
});
