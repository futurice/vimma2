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
            errTxt += ': ' + JSON.stringify(JSON.parse(xhr.responseText));
        } catch (exc) {
            // json parsing error
            errTxt += ': ' + xhr.responseText.substr(0, 100);
        }
    }
    return errTxt;
}

/*
 * Start at url, follow .next pages to end.
 * Call successCallback(results) or errCallback(errorText).
 */
function apiGetAll(url, successCallback, errCallback) {
    var results = [];
    function fetch() {
        if (!url) {
            successCallback(results);
            return;
        }

        $.ajax({
            url: url,
            success: function(data) {
                results = results.concat(data.results);
                url = data.next;
                fetch();
            },
            error: function() {
                var errTxt = getAjaxErr.apply(this, arguments);
                errCallback(errTxt);
            }
        });
    }
    fetch();
}
