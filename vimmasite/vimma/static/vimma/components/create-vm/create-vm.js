Polymer('create-vm', {
    loading: true,
    loadingSucceeded: false,

    observe: {
        prjIdx: 'computeHighlightCreate',
        scheduleid: 'computeHighlightCreate'
    },

    projects: [],
    initialProjectId: null, // initial project selection, optional
    prjIdx: null,   // selected project index

    providers: [],
    providersChanged: function() {
        if (this.providers.length) {
            this.provIdx = 0;
        }
    },
    provIdx: null,  // selected index
    provIdxChanged: function() {
        this.computeShownConfs();
        this.computeHighlightCreate();
    },

    all_vmconfigs: [],

    schedules: [],
    scheduleIdx: null,

    computeShownConfs: function() {
        var provId = null;
        if (this.provIdx != null) {
            provId = this.providers[this.provIdx].id;
        }
        this.shownConfs = this.all_vmconfigs.filter((function(vmc) {
            return vmc.provider == provId;
        }).bind(this));
    },
    shownConfs: [],
    shownConfsChanged: function() {
        this.shownConfsIdx = this.shownConfs.length ? 0 : null;
        this.async(this.shownConfsIdxChanged);
    },
    shownConfsIdx: null,
    shownConfsIdxChanged: function() {
        this.scheduleIdx = null;
        if (this.shownConfsIdx != null) {
            var s_id = this.shownConfs[this.shownConfsIdx].default_schedule;
            this.schedules.forEach((function(s, idx) {
                if (s.id == s_id) {
                    this.scheduleIdx = idx;
                }
            }).bind(this));
        }
        
        // request a reset of the type-specific ‘data’ for the new VM
        this.newVMData = null;
        this.computeNewVMType();
        this.computeHighlightCreate();
    },

    computeNewVMType: function() {
        if (this.shownConfsIdx == null) {
            this.newVMType = null;
            return;
        }
        var vmc = this.shownConfs[this.shownConfsIdx],
            prov = this.providers[this.provIdx];
        this.newVMType = prov.type;
    },
    newVMType: null,

    /*
     * Type-specific data for the new VM. We bind this to the type-specific
     * <component>'s model. We signal to it that we want a reset of the data to
     * the type-specific default by setting this to null.
     */
    newVMData: null,

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.loading = true;
        this.$.ajax.fire('start');

        this.projects = [];
        this.prjIdx = null;
        this.providers = [];
        this.provIdx = null;
        this.all_vmconfigs = [];
        this.schedules = [];

        this.loadItems();
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

    loadItems: function() {
        var ok = (function(resultArr) {
            var i = 0;
            this.projects = resultArr[i++];
            this.providers = resultArr[i++];
            this.all_vmconfigs = resultArr[i++];
            this.schedules = resultArr[i++];

            if (this.projects.length && this.initialProjectId != null) {
                this.projects.forEach((function(p, idx) {
                    if (p.id == this.initialProjectId) {
                        this.prjIdx = idx;
                    }
                }).bind(this));
            }

            this.loadSuccess();
        }).bind(this);

        apiGetAll([vimmaApiProjectList, vimmaApiProviderList,
                vimmaApiVMConfigList, vimmaApiScheduleList],
                ok, this.loadFail.bind(this));
    },

    highlightCreateBtn: false,
    computeHighlightCreate: function() {
        this.highlightCreateBtn = this.prjIdx != null && this.provIdx != null
            && this.shownConfsIdx != null && this.scheduleIdx != null;
    },

    createVM: function() {
        var prj = this.projects[this.prjIdx] || null,
            vmc = this.shownConfs[this.shownConfsIdx] || null,
            sched = this.schedules[this.scheduleIdx] || null;

        this.$.ajax.fire('start');
        $.ajax({
            url: vimmaEndpointCreateVM,
            type: 'POST',
            contentType: 'application/json; charset=UTF-8',
            headers: {
                'X-CSRFToken': $.cookie('csrftoken')
            },
            data: JSON.stringify({
                project:    prj && prj.id,
                vmconfig:   vmc && vmc.id,
                schedule:   sched && sched.id,
                data:       this.newVMData
            }),
            success: (function(data) {
                this.$.ajax.fire('end', {success: true});
                this.fire('vm-created');
            }).bind(this),
            error: (function() {
                var errorText = getAjaxErr.apply(this, arguments);
                this.$.ajax.fire('end', {success: false, errorText: errorText});
            }).bind(this)
        });
    }
});
