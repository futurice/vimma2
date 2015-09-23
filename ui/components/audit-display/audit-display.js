Polymer({
  is: 'audit-display',

  behaviors: [VimmaBehaviors.Equal],

  properties: {
    vm: {
      type: Object,
    },
    userid: {
      type: Number,
      value: -1
    },
    _auditLevels: {
      type: Number,
      readOnly: true,
      value: auditLevels
    },
    _minLevel: {
      type: Object,
      value: auditLevels[1]
    }
  },

  auditUrl: function(vm, name) {
    if(vm) {
      return url('audit-list');
    }
    return url('audit-list');
  },

  _minLevelChange: function(ev) {
    this.setParams('min_level', this._auditLevels[ev.target.selectedIndex].id);
    this.setParams('page', 1);
  },

  _getAuditLvlName: function(lvl) {
    if (lvl in auditNameForLevel) {
      return auditNameForLevel[lvl];
    }
    return lvl;
  },

  _prevPage: function() {
    this.setParams('page', uriparams(this.pageData.previous, 'page') || 1);
  },

  _nextPage: function() {
    this.setParams('page', uriparams(this.pageData.next, 'page'));
  },

  setParams: function(name, value) {
    p = {};
    p[name] = value;
    this.$.ajax.params = $.extend({}, this.$.ajax.params, p);
  },

  pageNumber: function() {
    return uriparams(this.pageData.url, 'page');
  }
});
