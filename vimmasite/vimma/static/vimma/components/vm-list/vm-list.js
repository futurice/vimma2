Polymer('vm-list', {
    /* Utilities for loading data */

    loading: true,
    success: null,
    errorText: null,

    ready: function() {
        this.reload();
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

    reload: function() {
        this.loading = true;
        this.success = null;
        this.errorText = null;

        this.profile = null;
        this.vms = [];
        this.projectsById = {};

        this.loadProfile();
    },

    /* Data model */

    profile: null,
    profileChanged: function() {
        var idSet = {};
        if (this.profile != null) {
            this.profile.projects.forEach(function(prjId) {
                idSet[prjId] = null;
            });
        }
        this.ownProjectSet = idSet;
    },
    // {id1:…, id2:…, …} for all project IDs the current user is a member of
    ownProjectSet: {},

    vms: [],
    vmsChanged: function() {
        var own = [], others = [];
        this.vms.forEach((function(vm) {
            if (vm.project in this.ownProjectSet) {
                own.push(vm);
            } else {
                others.push(vm);
            }
        }).bind(this));
        this.vmsInOwnProjects = own;
        this.vmsInOtherProjects = others;
    },
    vmsInOwnProjects: [],
    vmsInOtherProjects: [],
    showOtherVMs: false,

    // {id1: prj1, …} for all visible projects
    projectsById: {},

    toggleOtherVMs: function() {
        this.showOtherVMs = !this.showOtherVMs;
    },

    /* Functions loading the data */

    loadProfile: function() {
        var ok = (function(resultArr) {
            this.profile = resultArr[0][0];
            this.loadVMsProjects();
        }).bind(this);
        apiGetAll([vimmaApiProfileList + '?user=' + vimmaUserId],
                ok, this.loadFail.bind(this));
    },

    loadVMsProjects: function() {
        var ok = (function(resultArr) {
            var i = 0;
            this.vms = resultArr[i++];

            var prjById = {};
            resultArr[i++].forEach(function(prj) {
                prjById[prj.id] = prj;
            });
            this.projectsById = prjById;

            this.loadSuccess();
        }).bind(this);
        apiGetAll([vimmaApiVMList, vimmaApiProjectList],
                ok, this.loadFail.bind(this));
    }
});
