Polymer({
    is: 'schedule-list',

    properties: {
        _url: {
            type: String,
            readOnly: true,
            value: vimmaApiScheduleList
        },
        _loading: Boolean,
        _error: String,

        _apiData: {
            type: Array,
            observer: '_apiDataChanged'
        },
        /* [{id: 5}, …] because [5, …] doesn't behave well with ‘dom-repeat’
         * and array mutation.
         * Set when _apiData loads. Mutated when a schedule is created or
         * deleted.
         */
        _idObjs: Array
    },

    _apiDataChanged: function(newV, oldV) {
        this._idObjs = newV.map(function(v) {
            return {id: v.id};
        });
    },

    scheduleCreated: function(id) {
        this.unshift('_idObjs', {id: id});
    },
    _scheduleDeleted: function(ev) {
        var i, n = this._idObjs.length;
        for (i = 0; i < n; i++) {
            if (this._idObjs[i].id == ev.detail) {
                this.splice('_idObjs', i, 1);
                return;
            }
        }
        console.warn('Deleted schedule', ev.detail, 'not found');
    }
});