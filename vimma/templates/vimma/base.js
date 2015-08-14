var indexUrl = '{% url "index" %}',

    vimmaApiRoot = '{% url "api-root" %}',
    vimmaApiScheduleList = '{% url "schedule-list" %}',
    vimmaApiScheduleDetailRoot = apiDetailRootUrl(
            '{% url "schedule-detail" 0 %}'),
    vimmaApiTimeZoneList = '{% url "timezone-list" %}',
    vimmaApiProjectList = '{% url "project-list" %}',
    vimmaApiProjectDetailRoot = apiDetailRootUrl(
            '{% url "project-detail" 0 %}'),
    vimmaApiUserList = '{% url "user-list" %}',
    vimmaApiUserDetailRoot = apiDetailRootUrl(
            '{% url "user-detail" 0 %}'),

    vimmaApiDummyVMDetailRoot = apiDetailRootUrl(
            '{% url "dummyvm-detail" 0 %}'),
    vimmaApiDummyProviderList = '{% url "dummyprovider-list" %}',
    vimmaApiDummyVMConfigList = '{% url "dummyvmconfig-list" %}',

    vimmaApiAWSVMDetailRoot = apiDetailRootUrl(
            '{% url "awsvm-detail" 0 %}'),
    vimmaApiAWSProviderList = '{% url "awsprovider-list" %}',
    vimmaApiAWSProviderDetailRoot = apiDetailRootUrl(
            '{% url "awsprovider-detail" 0 %}'),
    vimmaApiAWSVMConfigList = '{% url "awsvmconfig-list" %}',
    vimmaApiAWSVMConfigDetailRoot = apiDetailRootUrl(
            '{% url "awsvmconfig-detail" 0 %}'),
    vimmaApiAWSFirewallRuleList = '{% url "awsfirewallrule-list" %}',
    vimmaApiAWSFirewallRuleDetailRoot = apiDetailRootUrl(
            '{% url "awsfirewallrule-detail" 0 %}'),

    vimmaApiAuditList = '{% url "audit-list" %}',
    vimmaApiPowerLogList = '{% url "powerlog-list" %}',
    vimmaApiVMExpirationDetailRoot = apiDetailRootUrl(
            '{% url "vmexpiration-detail" 0 %}'),
    vimmaApiFirewallRuleExpirationList =
        '{% url "firewallruleexpiration-list" %}',
    vimmaApiFirewallRuleList = '{% url "firewallrule-list" %}',

    vimmaEndpointCreateVM = '{% url "createVM" %}',
    vimmaEndpointPowerOnVM = '{% url "powerOnVM" %}',
    vimmaEndpointPowerOffVM = '{% url "powerOffVM" %}',
    vimmaEndpointRebootVM = '{% url "rebootVM" %}',
    vimmaEndpointDestroyVM = '{% url "destroyVM" %}',
    vimmaEndpointOverrideSchedule = '{% url "overrideSchedule" %}',
    vimmaEndpointChangeVMSchedule = '{% url "changeVMSchedule" %}',
    vimmaEndpointSetExpiration = '{% url "setExpiration" %}',
    vimmaEndpointCreateFirewallRule = '{% url "createFirewallRule" %}',
    vimmaEndpointDeleteFirewallRule = '{% url "deleteFirewallRule" %}',

    vimmaUserId = {{ user.id }},

    restPageSizeQueryParam = '{{pagination.page_size_query_param|escapejs}}',
    restMaxPageSize = {{pagination.max_page_size}},

    // [{id: …, name: …}, …]
    auditLevels = JSON.parse('{{audit_level_choices_json|escapejs}}'),
    // {id1: name1, id2: name2, …}
    auditNameForLevel = (function() {
        var result = {};
        auditLevels.forEach(function(a) {
            result[a.id] = a.name;
        });
        return result;
    })(),

    // [{value: …, label: …}, …]
    awsFirewallRuleProtocolChoices = JSON.parse(
            '{{aws_firewall_rule_protocol_choices_json|escapejs}}'),

    _dummy_end;

function uriparams(uri, name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"), results = regex.exec(uri);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}
