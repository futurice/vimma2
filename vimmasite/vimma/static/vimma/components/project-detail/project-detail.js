Polymer('project-detail', {
    frag: '',
    prjid: null,
    loading: true,
    success: null,
    errorText: null,

    model: null,
    profilesById: null, // {id1: p1, id2: p2, …}
    users: null,    // [u1, u2, …]
    usersById: null,    // {id1: u1, id2: u2, …}
    vms: null,
    vmsChanged: function() {
        this.vmIds = this.vms === null ? null : this.vms.map(function(vm) {
            return vm.id;
        });
    },
    vmIds: null,

    created: function() {
        this.tabs = [
            {key: 'vms', title: 'VMs'},
            {key: 'users', title: 'Users'}
        ];
    },

    observe: {
        '$.ajaxFrag.head': 'fragHeadChanged'
    },
    fragHeadChanged: function() {
        var i, key = this.$.ajaxFrag.head;
        for (i = 0; i < this.tabs.length; i++) {
            if (this.tabs[i].key == key) {
                this.selectedTabIdx = i;
                return;
            }
        }

        // without the async, #!/projects/1/ doesn't change to the vms URL
        this.async(function() {
            this.frag = this.tabs[0].key;
        });
    },

    selectedTabIdxChanged: function() {
        var key = this.tabs[this.selectedTabIdx].key;
        if (this.$.ajaxFrag.head != key) {
            this.frag = key;
        }
    },

    ready: function() {
        this.reload();
    },

    reload: function() {
        this.loading = true;
        this.success = null;
        this.errorText = null;

        this.model = null;
        this.profilesById = null;
        this.users = null;
        this.usersById = null;
        this.vms = null;
        this.vmIds = null;

        this.loadProject();
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
    loadProject: function() {
        var ok = (function(resultArr) {
            this.model = resultArr[0];
            this.loadProfiles();
        }).bind(this);
        apiGet([vimmaApiProjectDetailRoot + this.prjid + '/'],
                ok, this.loadFail.bind(this));
    },
    loadProfiles: function() {
        var ok = (function(resultArr) {
            var byId = {};
            resultArr[0].forEach(function(p) {
                byId[p.id] = p;
            });
            this.profilesById = byId;
            this.loadUsers();
        }).bind(this);
        apiGetAll([vimmaApiProfileList + '?projects=' + this.prjid],
                ok, this.loadFail.bind(this));
    },
    loadUsers: function() {
        var urls = [];
        Object.keys(this.profilesById).forEach((function(id) {
            var p = this.profilesById[id];
            urls.push(vimmaApiUserDetailRoot + p.user + '/');
        }).bind(this));
        var ok = (function(resultArr) {
            this.users = resultArr.sort(function(a, b) {
                var aN = a.first_name + ' ' + a.last_name,
                    bN = b.first_name + ' ' + b.last_name;
                if (aN < bN) {
                    return -1;
                }
                if (aN > bN) {
                    return 1;
                }
                return 0;
            });

            var byId = {};
            this.users.forEach(function(u) {
                byId[u.id] = u;
            });
            this.usersById = byId;
            this.loadVMs();
        }).bind(this);
        apiGet(urls, ok, this.loadFail.bind(this));
    },
    loadVMs: function() {
        var ok = (function(resultArr) {
            this.vms = resultArr[0];
            this.loadSuccess();
        }).bind(this);
        apiGetAll([vimmaApiVMList + '?project=' + this.prjid],
                ok, this.loadFail.bind(this));
    },

    onCoreSelect: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.selectedTab = detail.item.getAttribute('tabId');
        }
    }
});
