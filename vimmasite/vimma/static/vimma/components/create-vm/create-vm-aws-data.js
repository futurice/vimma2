Polymer('create-vm-aws-data', {
    data: null,
    dataChanged: function() {
        if (this.data == null) {
            this.async(this.setDefaultData);
        }
    },
    setDefaultData: function() {
        this.data = {
            name: '',
            region: ''
        };
        this.regionIdx = 4;
        this.async(this.regionIdxChanged);
    },

    regionIdx: null,
    regionIdxChanged: function() {
        this.data.region = this.regions[this.regionIdx];
    },

    created: function() {
        // avoid ‘shared state between instances’, though this is immutable
        this.regions = [
            'us-west-2',
            'ap-southeast-1',
            'us-gov-west-1',
            'ap-northeast-1',
            'sa-east-1',
            'cn-north-1',
            'ap-southeast-2',
            'us-east-1',
            'eu-west-1',
            'us-west-1'
        ];
        this.regions.sort();

        this.async(this.setDefaultData);
    },

    regionSelected: function(e, detail, sender) {
        e.stopPropagation();
        if (detail.isSelected) {
            this.data.region = detail.item.templateInstance.model.r;
        }
    }
});
