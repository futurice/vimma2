Polymer({
  is: 'create-vm',

  behaviors: [VimmaBehaviors.Equal],

  observers: [
  ],

  properties: {
    _expanded: {
      type: Boolean,
      value: false
    },

    createUrl: {
      type: String,
      value: vimmaEndpointCreateVM
    },

    projectsUrl: {
      type: String,
      value: vimmaApiProjectList
    },

    providersDummyUrl: {
      type: String,
      value: vimmaApiDummyProviderList
    },

    providersAwsUrl: {
      type: String,
      value: vimmaApiAWSProviderList
    },

    providers: {
      type: Array,
      computed: 'computeProviders(providersDummy,providersAws)'
    },

    schedulesUrl: {
      type: String,
      value: vimmaApiScheduleList
    },
    schedules: Array
  },

  computeProviders: function(dummy, aws) {
    return [].concat(dummy.results).concat(aws.results);
  },

  ready: function() {
  },

  scheduleSelected: function(k, detail) {
    this.$$('#schedule').value = k.currentTarget.dataItem.id;
  },

  providerSelected: function(k, detail) {
    this.$$('#provider').value = k.currentTarget.dataItem.id;
    this.$$('#config').value = k.currentTarget.dataConfig.id;
  },

  _toggle: function() {
    this._expanded = !this._expanded;
  },

  submitForm: function() {
    f = this.$$('#create-vm-form');
    f._requestBot.headers = {'X-CSRFToken': $.cookie('csrftoken')};
    f.submit();
  }
});
