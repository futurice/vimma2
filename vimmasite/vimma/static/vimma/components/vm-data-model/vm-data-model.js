(function() {
    // A sort of abstract superclass defining methods common to all subclasses.
    function VMModel(vm, provider, project, expiration) {
        this.vm = vm;
        this.provider = provider;
        this.project = project;
        this.expiration = expiration;
    }

    // Returns a string.
    VMModel.prototype.getExpiryDate = function() {
        return this.expiration.expires_at;
    };

    VMModel.prototype.getProjectName = function() {
        return this.project.name;
    };

    VMModel.prototype.isDestroyed = function() {
        return this.vm.destroyed_at !== null;
    };

    [
        'getName',
        'isOn',
    ].forEach(function(name) {
        VMModel.prototype[name] = function() {
            throw new Error('Not implemented');
        };
    });


    function DummyVMModel(vm, provider, project, expiration, dummy_vm) {
        VMModel.call(this, vm, provider, project, expiration);
        this.dummy_vm = dummy_vm;
    }
    DummyVMModel.prototype = Object.create(VMModel.prototype);

    DummyVMModel.prototype.getName = function() {
        return this.dummy_vm.name;
    };

    DummyVMModel.prototype.isOn = function() {
        return this.dummy_vm.poweredon;
    };


    function AWSVMModel(vm, provider, project, expiration, aws_vm) {
        VMModel.call(this, vm, provider, project, expiration);
        this.aws_vm = aws_vm;
    }
    AWSVMModel.prototype = Object.create(VMModel.prototype);

    AWSVMModel.prototype.getName = function() {
        return this.aws_vm.name;
    };

    AWSVMModel.prototype.isOn = function() {
        // Keep this in sync with aws.py
        switch (this.aws_vm.state) {
            case 'pending':
            case 'running':
            case 'stopping':
            case 'shutting-down':
                return true;

            case 'stopped':
            case 'terminated':
                return false;
        }

        console.warn('Unknown AWS VM state: ‘' + this.aws_vm.state + '’');
        return false;
    };


    /* Load the data model for the VM with vmid.
     * If anything fails, call errCallback(errorText).
     * Else call successCallback(vmDataModel).
     */
    function loadVM(vmid, successCallback, errCallback) {
        apiGet([vimmaApiVMDetailRoot + vmid + '/'], function(resArr) {
            loadProvPrjVmExp(resArr[0]);
        }, errCallback);

        function loadProvPrjVmExp(vm) {
            var provUrl = vimmaApiProviderDetailRoot + vm.provider + '/',
                prjUrl = vimmaApiProjectDetailRoot + vm.project + '/',
                vmExpUrl = vimmaApiVMExpirationDetailRoot + '?vm=' + vm.id;
            apiGet([provUrl, prjUrl, vmExpUrl], function(resArr) {
                var prov = resArr[0], prj = resArr[1],
                    vmExp = resArr[2].results[0];
                loadExp(vm, prov, prj, vmExp);
            }, errCallback);
        }

        function loadExp(vm, provider, project, vm_expiration) {
            var url = vimmaApiExpirationDetailRoot +
                vm_expiration.expiration + '/';
            apiGet([url], function(resArr) {
                makeVMModel(vm, provider, project, resArr[0]);
            }, errCallback);
        }

        function makeVMModel(vm, provider, project, expiration) {
            switch (provider.type) {
                case 'dummy':
                    makeDummyVMModel(vm, provider, project, expiration);
                    return;
                case 'aws':
                    makeAWSVMModel(vm, provider, project, expiration);
                    return;
                default:
                    errCallback('Unknown Provider type: ' + provider.type);
                    return;
            }
        }

        function makeDummyVMModel(vm, provider, project, expiration) {
            var url = vimmaApiDummyVMDetailRoot + '?vm=' + vm.id;
            apiGet([url], function(resArr) {
                var dummy_vm = resArr[0].results[0],
                    model = new DummyVMModel(vm, provider, project, expiration,
                            dummy_vm);
                successCallback(model);
            }, errCallback);
        }

        function makeAWSVMModel(vm, provider, project, expiration) {
            var url = vimmaApiAWSVMDetailRoot + '?vm=' + vm.id;
            apiGet([url], function(resArr) {
                var aws_vm = resArr[0].results[0],
                    model = new AWSVMModel(vm, provider, project, expiration,
                            aws_vm);
                successCallback(model);
            }, errCallback);
        }
    }

    /* Like loadVM but vmids is an array and successCallback gets called with
     * an array of data models.
     */
    function loadVMs(vmids, successCallback, errCallback) {
        if (!vmids.length) {
            setTimeout(function() {
                successCallback([]);
            }, 0);
            return;
        }

        var results = [],
            // a call has failed
            failed = false,
            // how many calls are in flight
            remaining = 0;
        vmids.forEach(function(vmid, idx) {
            results.push(null);
            loadVM(vmid, function(result) {
                if (failed) {
                    return;
                }
                results[idx] = result;
                remaining--;
                if (!remaining) {
                    successCallback(results);
                }
            }, function(errorText) {
                if (failed) {
                    return;
                }
                this.failed = true;
                errCallback(errorText);
            });
            remaining++;
        });
    }

    /* Like loadVMs but it loads all VMs.
     * If destroyed is a Boolean, it only loads destroyed/non-destroyed VMs.
     * Else (e.g. destroyed is ‘undefined’ or ‘null’) it loads all VMs.
     */
    function loadAllVMs(destroyed, successCallback, errCallback) {
        apiGetAll([vimmaApiVMList], function(resArr) {
            var vms = resArr[0];
            if (typeof(destroyed) === "boolean") {
                vms = vms.filter(function(vm) {
                    return (vm.destroyed_at !== null) === destroyed;
                });
            }
            loadVMs(vms.map(function(vm) {
                return vm.id;
            }), successCallback, errCallback);
        }, errCallback);
    }

    Polymer({
        is: 'vm-data-model',

        loadVM: loadVM,
        loadVMs: loadVMs,
        loadAllVMs: loadAllVMs
    });
})();
