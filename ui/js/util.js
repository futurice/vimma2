/* "api/MyObject/0/" → "api/MyObject/" */
function apiDetailRootUrl(apiDetailUrl) {
    var suffix = "/0/";
    if (apiDetailUrl.substr(-suffix.length) != suffix) {
        throw 'Invail detail URL "' + apiDetailUrl + '"';
    }
    return apiDetailUrl.substring(0, apiDetailUrl.length - (suffix.length-1));
}

/*
 * Recursively obj, which must be ‘clonable’.
 *
 * Numbers, booleans and strings are clonable.
 * Plain JS objects and arrays are clonable if all their values are clonable.
 */
function clone(obj) {
    if (Array.isArray(obj)) {
        return obj.map(function(elem) {
            return clone(elem);
        });
    }

    if (obj === null || obj === undefined) {
        return obj;
    }

    switch (typeof(obj)) {
        case 'number':
        case 'string':
        case 'boolean':
            return obj;
        default:
            var result = {};
            for (var k in obj) {
                result[k] = clone(obj[k]);
            }
            return result;
    }
}

/*
 * Recursively compare ‘clonable’ objects (as defined by function clone()).
 */
function sameModels(a, b) {
    // this ‘===’ test is meant as a shortcut way out
    if (a === b) {
        return true;
    }

    var i;

    if (Array.isArray(a)) {
        if (!Array.isArray(b)) {
            return false;
        }
        if (a.length != b.length) {
            return false;
        }

        for (i = 0; i < a.length; i++) {
            if (!sameModels(a[i], b[i])) {
                return false;
            }
        }
        return true;
    }

    if (typeof(a) != typeof(b)) {
        return false;
    }

    if (a === null || b === null) {
        return a === b;
    }

    switch (typeof(a)) {
        case 'undefined':
        case 'number':
        case 'string':
        case 'boolean':
            return a === b;

        default:
            var aKeys = Object.keys(a).sort(), bKeys = Object.keys(b).sort();
            if (!sameModels(aKeys, bKeys)) {
                return false;
            }
            for (i = 0; i < aKeys.length; i++) {
                if (!sameModels(a[aKeys[i]], b[bKeys[i]])) {
                    return false;
                }
            }
            return true;
    }
}


/*
 * Overwrite base fields with those in ext1, then ext2, etc. and return base.
 *
 * extend(base [, ext1, ext2, …, extn]);
 */
function extend(base) {
    for (var i = 1; i < arguments.length; i++) {
        var arg = arguments[i];
        Object.keys(arg).forEach(function(k) {
            base[k] = arg[k];
        });
    }
    return base;
}
