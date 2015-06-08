Polymer('create-vm-aws-data', {
    // see ../vm-detail/vm-detail.js for the ‘loading’ pattern
    loading: false,
    loadingSucceeded: false,

    /*
     * Whether to trigger another reload after the current one finishes.
     * E.g. vmconf_idChanged can fire while we are already loading; when that
     * loading finishes, start another one.
     */
    loadAgain: false,

    ready: function() {
        this.reload();
    },

    reload: function() {
        if (this.loading) {
            this.loadAgain = true;
            return;
        }

        this.loadAgain = false;
        this.$.ajax.fire('start');
        this.loading = true;

        this.awsvmconf = null;
        this.loadAWSVMConf();
    },
    loadFail: function(errorText) {
        this.$.ajax.fire('end', {success: false, errorText: errorText});

        this.loading = false;
        this.loadingSucceeded = false;

        if (this.loadAgain) {
            this.reload();
        }
    },
    loadSuccess: function() {
        this.$.ajax.fire('end', {success: true});

        this.loading = false;
        this.loadingSucceeded = true;

        if (this.loadAgain) {
            this.reload();
        }
    },

    loadAWSVMConf: function() {
        var ok = (function(resultArr) {
            this.awsvmconf = resultArr[0].results[0];
            this.setDefaultData();
            this.loadSuccess();
        }).bind(this);
        apiGet([vimmaApiAWSVMConfigDetailRoot + '?vmconfig=' + this.vmconf_id],
                ok, this.loadFail.bind(this));
    },

    vmconf_id: null,
    vmconf_idChanged: function() {
        this.reload();
    },

    awsvmconf: null,

    data: null,
    dataChanged: function() {
        if (this.data == null) {
            this.async(this.setDefaultData);
        }
    },
    setDefaultData: function() {
        if (this.awsvmconf == null) {
            return;
        }

        this.data = {
            name: '',
            root_device_size: this.awsvmconf.root_device_size,
            root_device_volume_type: this.awsvmconf.root_device_volume_type
        };
    },

    observe: {
        'data.root_device_size': 'checkRootDevSize',
        'data.root_device_volume_type': 'setHddTypeIdx'
    },

    checkRootDevSize: function() {
        if (this.data) {
            if (typeof(this.data.root_device_size) == 'string') {
                var n = parseInt(this.data.root_device_size);
                this.hddSizeInvalid = !Number.isInteger(n) ||
                    n < this.minHddSize || n > this.maxHddSize;
                if (!this.hddSizeInvalid) {
                    this.data.root_device_size = n;
                }
            }
        }
    },

    hddSizeInvalid: false,
    minHddSize: AWS_ROOT_DEVICE_MIN_SIZE,
    maxHddSize: AWS_ROOT_DEVICE_MAX_SIZE,

    hddTypeChoices: aws_volume_type_choices_json,
    hddTypeIdx: 0,
    hddTypeIdxChanged: function() {
        this.data.root_device_volume_type =
            this.hddTypeChoices[this.hddTypeIdx].value;
    },
    setHddTypeIdx: function() {
        if (this.data == null) {
            return;
        }
        this.hddTypeChoices.forEach((function(c, i) {
            if (c.value == this.data.root_device_volume_type) {
                this.hddTypeIdx = i;
            }
        }).bind(this));
    }
});
