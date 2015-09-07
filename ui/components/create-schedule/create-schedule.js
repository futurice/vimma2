Polymer({
  is: 'create-schedule',

  ready: function() {
    this.$['create-schedule-form']._requestBot.headers = {'X-CSRFToken': $.cookie('csrftoken')};
  },

  behaviors: [VimmaBehaviors.Equal],

  properties: {
    _expanded: {
      type: Boolean,
      notify: true,
      value: false
    },

    _toggleClass: {
      type: String,
      computed: 'toggleClass(_expanded)'
    },

    createUrl: {
      type: String,
      value: vimmaApiScheduleList
    },

    _tzApiUrl: {
      type: String,
      value: vimmaApiTimeZoneList
    }
  },

  _toggle: function() {
    this._expanded = !this._expanded;
  },

  toggleClass: function(expanded) {
    return (expanded) ? 'visible' : 'hidden';
  },

  timezoneSelected: function(ev) {
    this.set('timezone', this.timezones.results[ev.target.selectedIndex]['id']);
  },

  submitForm: function() {
    f = this.$$('#create-schedule-form');
    f.submit();
  }
});
