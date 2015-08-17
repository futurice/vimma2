Polymer({
  is: 'create-vm',

  behaviors: [VimmaBehaviors.Equal],

  properties: {
    _expanded: {
      type: Boolean,
      value: false,
      observer: '_expandedChanged'
    },

    projectsUrl: {
      type: String,
      value: vimmaApiProjectList
    },
    projects: {
      type: Array,
      observer: 'projectsChanged'
    },
    _selPrj: Object,

    providersUrl: {
      type: String,
      value: vimmaApiDummyProviderList
    },
    providers: {
      type: Array,
      observer: '_providersChanged'
    },
    _selProvider: Object,

    configsUrl: {
      type: String,
      value: vimmaApiDummyVMConfigList
    },
    configs: Array,
    _vmcfgsForProvider: {
      type: Array,
      computed: '_computeVmCfgsForProvider(configs, _selProvider)',
      observer: '_vmcfgsForProviderChanged'
    },
    _selVmcfg: Object,

    schedulesUrl: {
      type: String,
      value: vimmaApiScheduleList
    },
    schedules: Array,
    _selSchedule: Object,

    _loading: {
      type: Boolean,
      computed: '_computeLoading(_prjsLoading, _providersLoading, _vmcfgsLoading, _schedulesLoading)'
    },
    _loadErr: {
      type: String,
      computed: '_computeError(_prjsErr, _providersErr, _vmcfgsErr, _schedulesErr)'
    },

    _comment: String,

    /* Provider-specific data.
     * The type-specific components should overwrite this when they are
     * created/ready, and then can just change fields inside the object.
     * We just send the whole data object in the ‘create’ API call.
     */
              _data: Object,

              _createInFlight: {
type: Boolean,
      value: false
              },
_createError: {
type: String,
      value: ''
              }
  },

    observers: [
      '_setSelectedSchedule(schedules, _selVmcfg)'
    ],

    _expandedChanged: function(newV, oldV) {
      if (newV) {
        this._comment = '';
        this._createError = '';
      }
    },

    _toggle: function() {
      this._expanded = !this._expanded;
    },

    _computeLoading: function() {
      var i, n = arguments.length, crt;
      for (i = 0; i < n; i++) {
        crt = arguments[i];
        if (crt) {
          return true;
        }
      }
      return false;
    },
    _computeError: function() {
      var i, n = arguments.length, crt;
      for (i = 0; i < n; i++) {
        crt = arguments[i];
        if (crt) {
          return crt;
        }
      }
      return '';
    },

    projectsChanged: function(newV, oldV) {
      this._selPrj = newV[0];
    },
    projectSelected: function(ev) {
      this._selPrj = this._prjs[ev.target.selectedIndex];
    },

    _providersChanged: function(newV, oldV) {
      console.log("providersChanged",newV);
      //this._selProvider = newV[0];
      newV.results.forEach(function(p) {
        if (p.default) {
          this._selProvider = p;
        }
      }, this);
    },
    _providerSelected: function(ev) {
      this._selProvider = this._providers[ev.target.selectedIndex];
    },

    _computeVmCfgsForProvider: function(vmcfgs, selProvider) {
      return vmcfgs.results.filter(function(c) {
        return c.provider == selProvider.id;
      }, this);
    },
    _vmcfgsForProviderChanged: function(newV, oldV) {
      this._selVmcfg = newV[0];
      newV.forEach(function(c) {
        if (c.default) {
          this._selVmcfg = c;
        }
      }, this);
    },
    _vmcfgSelected: function(ev) {
      this._selVmcfg = this._vmcfgsForProvider[ev.target.selectedIndex];
    },

    _setSelectedSchedule: function(schedules, selVmcfg) {
      //this._selSchedule = schedules[0];
      schedules.results.forEach(function(s) {
        if (s.id == selVmcfg.default_schedule) {
          this._selSchedule = s;
        }
      }, this);
    },
    _scheduleSelected: function(ev) {
      this._selSchedule = this.schedules.results[ev.target.selectedIndex];
    },

    _create: function() {
      this._createInFlight = true;

      $.ajax({
        url: vimmaEndpointCreateVM,
        type: 'POST',
        contentType: 'application/json; charset=UTF-8',
        headers: {
          'X-CSRFToken': $.cookie('csrftoken')
        },
        data: JSON.stringify({
          project: this._selPrj.id,
          vmconfig: this._selVmcfg.id,
          schedule: this._selSchedule.id,
          comment: this._comment,
          data: this._data
        }),
        complete: (function() {
          this._createInFlight = false;
        }).bind(this),
        success: (function() {
          this._createError = '';
          this._toggle();
          this.fire('vm-created');
        }).bind(this),
        error: (function(xhr, txtStatus, saveErr) {
          var errorText = getAjaxErr.apply(this, arguments);
          this._createError = errorText;
        }).bind(this)
      });
    }
              });
