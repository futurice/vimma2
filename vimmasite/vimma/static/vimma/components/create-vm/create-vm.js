Polymer('create-vm', {
    projects: [],

    providers: [],
    providersChanged: function() {
        var providersById = {};
        this.providers.forEach(function(p) {
            providersById[p.id] = p;
        });
        this.providersById = providersById;
    },
    providersById: {},

    vmconfigs: [],
    vmconfigsChanged: function() {
        var vmconfigsById = {};
        this.vmconfigs.forEach(function(v) {
            vmconfigsById[v.id] = v;
        });
        this.vmconfigsById = vmconfigsById;
    },
    vmconfigsById: {},

    schedules: [],

    // initial load and subsequent full reloads
    loading: true,
    success: null,
    errorText: null,

    prjid: null,    // chosen project
    provid: null,   // chosen provider
    providChanged: function() {
        this.vmconfigid = null;

        this.computeVMConfigsForProvider();
        this.computeHighlightCreate();
    },
    vmconfigsForProvider: [],
    computeVMConfigsForProvider: function() {
        this.vmconfigsForProvider = this.vmconfigs.filter((function(vmc) {
            return vmc.provider == this.provid;
        }).bind(this));
    },
    vmconfigid: null,   // chosen vmconfig
    vmconfigidChanged: function() {
        // request a reset of the type-specific ‘data’ for the new VM
        this.newVMData = null;

        this.computeNewVMType();
        this.computeHighlightCreate();
    },
    scheduleid: null,   // chosen schedule

    newVMType: null,
    computeNewVMType: function() {
        if (this.vmconfigid == null) {
            this.newVMType = null;
            return;
        }
        var vmc = this.vmconfigsById[this.vmconfigid],
            prov = this.providersById[vmc.provider];
        this.newVMType = prov.type;
    },

    /*
     * Type-specific data for the new VM. We bind this to the type-specific
     * <component>'s model. We signal to it that we want a reset of the data to
     * the type-specific default by setting this to null.
     */
    newVMData: null,

    /*
     * AJAX operations while the element is loaded:
     * ― create new VM
     */
    ajaxInProgress: false,
    ajaxSuccess: true,
    ajaxErrTxt: '',

    observe: {
        prjid: 'computeHighlightCreate',
        scheduleid: 'computeHighlightCreate'
    },

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.loading = true;
        this.success = null;
        this.errorText = null;

        this.projects = [];
        this.providers = [];
        this.vmconfigs = [];
        this.schedules = [];

        this.loadItems();
    },
    loadFail: function(errorText) {
        this.loading = false;
        this.success = false;
        this.errorText = errorText;
    },
    loadSuccess: function() {
        this.loading = false;
        this.success = true;
    },

    loadItems: function() {
        var ok = (function(resultArr) {
            var i = 0;
            this.projects = resultArr[i++];
            this.providers = resultArr[i++];
            this.vmconfigs = resultArr[i++];
            this.schedules = resultArr[i++];

            this.loadSuccess();
        }).bind(this);

        apiGetAll([vimmaApiProjectList, vimmaApiProviderList,
                vimmaApiVMConfigList, vimmaApiScheduleList],
                ok, this.loadFail.bind(this));
    },

    projectSelected: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.prjid = detail.item.templateInstance.model.p.id;
        }
    },
    providerSelected: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.provid = detail.item.templateInstance.model.p.id;
        }
    },
    vmconfigSelected: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.vmconfigid = detail.item.templateInstance.model.c.id;
        }
    },
    scheduleSelected: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.scheduleid = detail.item.templateInstance.model.s.id;
        }
    },

    highlightCreateBtn: false,
    computeHighlightCreate: function() {
        this.highlightCreateBtn = Boolean(this.prjid && this.provid &&
                this.vmconfigid && this.scheduleid);
    },

    createVM: function() {
        this.ajaxInProgress = true;
        $.ajax({
            url: vimmaEndpointCreateVM,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                project:    this.prjid,
                vmconfig:   this.vmconfigid,
                schedule:   this.scheduleid,
                data:       this.newVMData
            }),
            complete: (function(data) {
                this.ajaxInProgress = false;
            }).bind(this),
            success: (function(data) {
                this.ajaxSuccess = true;
                this.fire('vm-created');
            }).bind(this),
            error: (function() {
                this.ajaxSuccess = false;
                this.ajaxErrTxt = getAjaxErr.apply(this, arguments);
            }).bind(this)
        });
    }
});
