(function() {
    var fragPrefix = '#!', fragSep = '/';

    Polymer({
        is: 'frag-util',

        getFragPrefix: function() {
            return fragPrefix;
        },
        getFragSep: function() {
            return fragSep;
        },

        setFrag: function(frag) {
            // doesn't trigger 'hashchange' event listeners
            history.pushState(null, '', fragPrefix + frag);
        },
        getFrag: function() {
            var f = window.location.hash;
            if (f.slice(0, fragPrefix.length) == fragPrefix) {
                return f.slice(fragPrefix.length);
            }
            return '';
        },

        // "a/b/c" → "a"
        fragHead: function(frag) {
            var idx = frag.indexOf(fragSep);
            if (idx == -1) {
                return frag;
            }
            return frag.slice(0, idx);
        },

        // "a/b/c" → "b/c", "a" → ""
        fragTail: function(frag) {
            var idx = frag.indexOf(fragSep);
            if (idx == -1) {
                return "";
            }
            return frag.slice(idx+1);
        },

        // "a", "b/c" → "a/b/c"
        fragJoin: function(head, tail) {
            if (!head.length || !tail.length) {
                return head + tail;
            }
            return head + fragSep + tail;
        }
    });
})();
