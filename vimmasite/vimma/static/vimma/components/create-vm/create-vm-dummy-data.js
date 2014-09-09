Polymer('create-vm-dummy-data', {
    data: null,
    dataChanged: function() {
        if (this.data == null) {
            // without setTimeout, the data field in <create-vm> gets
            // disconnected from our own.
            setTimeout(this.setDefaultData.bind(this), 0);
        }
    },
    setDefaultData: function() {
        this.data = {
            name: ''
        };
    },

    created: function() {
        this.setDefaultData();
    }
});
