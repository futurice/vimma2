Polymer('human-size', {
    n: 0,
    unit: '?',
    sayplural: false,
    multiples: [],

    created: function() {
        this.displayItems = [];
    },
    ready: function() {
        var x = Math.abs(Math.round(this.n)),
            crtUnit = this.unit, crtSayPlural = this.sayplural,
            nextIdx = 0,
            r;

        if (!x) {
            this.displayItems.push({
                n: 0,
                name: this.unit,
                sayplural: this.sayplural
            });
            return;
        }

        while (x) {
            var next = null;
            if (nextIdx < this.multiples.length) {
                next = this.multiples[nextIdx++];
            }

            if (next && x >= next.n) {
                r = x % next.n;
                x = Math.floor(x / next.n);
            } else {
                r = x;
                x = 0;
            }

            if (r) {
                this.displayItems.push({
                    n: r,
                    name: crtUnit,
                    sayplural: crtSayPlural
                });
            }

            if (next) {
                crtUnit = next.name;
                crtSayPlural = next.sayplural;
            }
        }
        this.displayItems.reverse();
    }
});
