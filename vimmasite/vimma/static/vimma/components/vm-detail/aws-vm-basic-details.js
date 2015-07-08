Polymer({
    is: 'aws-vm-basic-details',

    properties: {
        // The AWSVMModel instance.
        vm: Object
    },

    _getName: function(vm) {
        return vm.getName();
    }
});
