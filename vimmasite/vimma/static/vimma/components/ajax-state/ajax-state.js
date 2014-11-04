/*
Element used to track the state and success of AJAX calls.

Fire events on this component and read its properties.
.fire('start') before you make the AJAX call(s).
After all have completed:
.fire('end', {success: true})
or
.fire('end', {success: false, errorText: string})
*/
Polymer('ajax-state', {
    inProgress: false,
    success: true,
    errorText: '',

    onStart: function(ev) {
        ev.stopPropagation();
        if (this.inProgress) {
            throw 'start fired while inProgress';
        }
        this.inProgress = true;
    },

    onEnd: function(ev, detail, sender) {
        ev.stopPropagation();
        if (!this.inProgress) {
            throw 'end fired while not inProgress';
        }
        this.inProgress = false;
        this.success = detail.success;
        this.errorText = this.success ? '' : detail.errorText;
    }
});
