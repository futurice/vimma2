/*
Element used to track the state and success of AJAX calls.

Fire events on this component and read its properties.
.fire('start') before you make the AJAX call(s).
After all have completed:
.fire('end', {success: true})
or
.fire('end', {success: false, errorText: string})

At every .fire('start'), .token is set to a new Object.
Example:
.fire('start')
save a copy of the token and make an asynchronous call
.fire('end', {success: false, errorText: 'canceled'})
.fire('start')
the asynchronous call runs and sees that its copy of the token is outdated
*/
Polymer('ajax-state', {
    inProgress: false,
    token: new Object(),
    success: true,
    errorText: '',

    onStart: function(ev) {
        ev.stopPropagation();
        if (this.inProgress) {
            throw 'start fired while inProgress';
        }
        this.inProgress = true;
        this.token = new Object();
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
