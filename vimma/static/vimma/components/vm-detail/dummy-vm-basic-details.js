Polymer({
    is: 'dummy-vm-basic-details',

    properties: {
        // The DummyVMModel instance.
        vm: Object
    },

    _getName: function(vm) {
        return vm.getName();
    }
});
