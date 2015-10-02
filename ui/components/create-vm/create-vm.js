Polymer({
  is: 'create-vm',

  behaviors: [VimmaBehaviors.Equal],

  observers: [
  ],

  listeners: {'iron-form-response': 'formResponse'},


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
      value: '#'
    },

    projectsUrl: {
      type: String,
      value: vimmaApiProjectList
    },

    providers: {
      type: Array,
      computed: 'computeProviders(providersDummy, providersAws)'
    },

    schedulesUrl: {
      type: String,
      value: vimmaApiScheduleList
    },
    schedules: Array,
    provider_type: String
  },

  providersDummyUrl: function() {
    return url('dummyprovider-list');
  },

  providersAwsUrl: function() {
    return url('awsprovider-list');
  },

  computeProviders: function(dummy, aws) {
    return [].concat(dummy.results).concat(aws.results);
  },

  ready: function() {
  },

  scheduleSelected: function(k, detail) {
    this.$$('#schedule').value = k.currentTarget.dataItem.id;
    this.chosen(k.currentTarget, '.schedule-container div.box')
  },

  providerSelected: function(k, detail) {
    this.$$('#provider').value = k.currentTarget.dataItem.id;
    this.$$('#config').value = k.currentTarget.dataConfig.id;
    this.chosen(k.currentTarget, '.provider-container div.box')
    this.provider_type = k.currentTarget.dataConfig.content_type.app_label;
    this.createUrl = url(this.provider_type+'vm-create');
  },

  chosen: function(el, container) {
    $(container).removeClass('chosen');
    $(el).toggleClass('chosen');
  },

  _toggle: function() {
    this._expanded = !this._expanded;
  },

  toggleClass: function(expanded) {
    return (expanded) ? 'visible' : 'hidden';
  },

  submitForm: function() {
    f = this.$$('#create-vm-form');
    f._requestBot.headers = {'X-CSRFToken': $.cookie('csrftoken')};
    f.submit();
  },

  formResponse: function(ev) {
    // spread news of new vm in the fold
    this.fire('vm-created', {
      provider: this.provider_type,
      ev: ev,
      form: this.$$('#create-vm-form')});
    // close create dialog
    this._toggle();
  },
});
