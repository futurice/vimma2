Polymer('create-vm-dummy-data', {
    data: null,
    dataChanged: function() {
        if (this.data == null) {
            this.async(this.setDefaultData);
        }
    },
    setDefaultData: function() {
        this.data = {
            name: '',
            delay: 5
        };
    },

    observe: {
        'data.delay': 'computeDelay'
    },

    created: function() {
        this.setDefaultData();
    },

    computeDelay: function() {
        if (this.data) {
            if (typeof(this.data.delay) == 'string') {
                this.data.delay = parseInt(this.data.delay);
            }
        }
    }
});
