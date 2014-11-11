/* "api/MyObject/0/" → "api/MyObject/" */
function apiDetailRootUrl(apiDetailUrl) {
    var suffix = "/0/";
    if (apiDetailUrl.substr(-suffix.length) != suffix) {
        throw 'Invail detail URL "' + apiDetailUrl + '"';
    }
    return apiDetailUrl.substring(0, apiDetailUrl.length - (suffix.length-1));
}

/*
 * Return a string describing the error, from the args of jQuery's ajax.error
 * function.
 */
function getAjaxErr(xhr, txtStatus, errThrown) {
    console.error(xhr, txtStatus, errThrown);
    var errTxt = 'Error';
    if (xhr.responseText) {
        try {
            // JSON response is an explanation of the problem.
            // Anything else is probably a huge html page
            // describing server misconfiguration.
            var jsonData = JSON.parse(xhr.responseText);
            // object has exactly 1 key, 'error' (its value can have any type)
            if ('error' in jsonData && Object.keys(jsonData).length == 1) {
                jsonData = jsonData.error;
            }
            errTxt += ': ' + JSON.stringify(jsonData);
        } catch (exc) {
            // json parsing error
            errTxt += ': ' + xhr.responseText;
        }
    }
    return errTxt;
}

/*
 * Get the object at each url in urlArray. If anything fails, call
 * errCallback(errorText). Else call successCallback(resultsArray).
 * resultsArray[i] is the item from urlArray[i].
 */
function apiGet(urlArray, successCallback, errCallback) {
    if (!urlArray.length) {
        successCallback([]);
    }

    var resultsArray = [],
        // a call has failed
        failed = false,
        // how many calls haven't completed yet
        remaining = 0;

    urlArray.forEach(function() {
        resultsArray.push(null);
    });

    function fetchIdx(idx) {
        $.ajax({
            url: urlArray[idx],
            success: function(data) {
                if (failed) {
                    return;
                }
                resultsArray[idx] = data;
                remaining--;
                if (!remaining) {
                    successCallback(resultsArray);
                }
            },
            error: function() {
                if (failed) {
                    return;
                }
                var errTxt = getAjaxErr.apply(this, arguments);
                errCallback(errTxt);
                failed = true;
            }
        });
    }

    urlArray.forEach(function(url, idx) {
        fetchIdx(idx);
        remaining++;
    });
}

/*
 * Start at each url in urlArray, follow .next pages to end.
 * If any call fails, call errCallback(errorText) and stop.
 * Else call successCallback(resultsArray).
 * resultsArray.length == urlArray.length
 * resultsArray[i] is itself an array with the data for urlArray[i].
 */
function apiGetAll(urlArray, successCallback, errCallback) {
    var resultsArray = [],
        // completedArray[i] == true if urlArray[i] finished successfully
        completedArray = [],
        // a call has failed: remaining url fetchers stop paging
        failed = false,
        // how many urls haven't reached the last page yet
        remaining = 0;

    urlArray.forEach(function() {
        resultsArray.push([]);
        completedArray.push(false);
    });

    // fetcher for urlArray[i] completed
    function done(i, results) {
        if (completedArray[i]) {
            throw i + ' completed multiple times';
        }
        if (failed) {
            return;
        }
        completedArray[i] = true;
        resultsArray[i] = results;
        remaining--;
        if (remaining == 0) {
            successCallback(resultsArray);
        }
    }

    // a call failed
    function fail(errorText) {
        if (failed) {
            return;
        }
        failed = true;
        errCallback(errorText);
    }

    function fetchIdx(i) {
        var results = [];
        function fetchUrl(url) {
            if (!url) {
                done(i, results);
                return;
            }
            if (failed) {
                return;
            }

            $.ajax({
                url: url,
                success: function(data) {
                    results = results.concat(data.results);
                    fetchUrl(data.next);
                },
                error: function() {
                    var errTxt = getAjaxErr.apply(this, arguments);
                    fail(errTxt);
                }
            });
        }
        fetchUrl(urlArray[i]);
    }

    urlArray.forEach(function(url, idx) {
        fetchIdx(idx);
        remaining++;
    });
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


var ajaxFragPrefix = '#!', ajaxFragSep = '/';

function setAjaxFrag(frag) {
    // doesn't trigger 'hashchange' event listeners
    history.pushState(null, '', ajaxFragPrefix + frag);
}

function getAjaxFrag() {
    var f = window.location.hash;
    if (f.slice(0, ajaxFragPrefix.length) == ajaxFragPrefix) {
        return f.slice(ajaxFragPrefix.length);
    }
    return '';
}

// "a/b/c" → "a"
function ajaxFragHead(frag) {
    var idx = frag.indexOf(ajaxFragSep);
    if (idx == -1) {
        return frag;
    }
    return frag.slice(0, idx);
}

// "a/b/c" → "b/c", "a" → ""
function ajaxFragTail(frag) {
    var idx = frag.indexOf(ajaxFragSep);
    if (idx == -1) {
        return "";
    }
    return frag.slice(idx+1);
}

// "a", "b/c" → "a/b/c"
function ajaxFragJoin(head, tail) {
    if (!head.length || !tail.length) {
        return head + tail;
    }
    return head + ajaxFragSep + tail;
}
