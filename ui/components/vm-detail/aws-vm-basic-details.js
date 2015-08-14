Polymer({
    is: 'aws-vm-basic-details',

    properties: {
        vm: Object
    },

    getName: function() {
        return this.vm.getName();
    }
});
