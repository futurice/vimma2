Polymer({
  is: 'aws-firewall-rules',

  properties: {
    vm: {
      type: Object,
      observer: 'vmChanged'
    }
  },

  vmChanged: function(newV, oldV) {
    this._reload();
  },

  _reload: function() {
  },

  _getPortDisplay: function(model) {
    var a = model.aws_fw_rule.from_port, b = model.aws_fw_rule.to_port;
    if (a === b) {
      return a;
    }
    return a + '–' + b;
  },

  _delete: function(ev) {
    // TODO: delete fw-rule
  }
});
