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
    vimmaApiAuditList = '{% url "audit-list" %}',

    vimmaApiDummyVMDetailRoot = apiDetailRootUrl(
            '{% url "dummyvm-detail" 0 %}'),
    vimmaApiDummyProviderList = '{% url "dummyprovider-list" %}',
    vimmaApiDummyConfigList = '{% url "dummyconfig-list" %}',
    vimmaApiDummyAuditList = '{% url "audit-list" %}',
    vimmaApiDummyPowerLogList = '{% url "dummypowerlog-list" %}',

    vimmaApiAwsVMDetailRoot = apiDetailRootUrl(
            '{% url "awsvm-detail" 0 %}'),
    vimmaApiAwsProviderList = '{% url "awsprovider-list" %}',
    vimmaApiAwsProviderDetailRoot = apiDetailRootUrl(
            '{% url "awsprovider-detail" 0 %}'),
    vimmaApiAwsConfigList = '{% url "awsconfig-list" %}',
    vimmaApiAwsConfigDetailRoot = apiDetailRootUrl(
            '{% url "awsconfig-detail" 0 %}'),
    vimmaApiAwsFirewallRuleList = '{% url "awsfirewallrule-list" %}',
    vimmaApiAwsFirewallRuleDetailRoot = apiDetailRootUrl(
            '{% url "awsfirewallrule-detail" 0 %}'),
    vimmaApiAwsAuditList = '{% url "audit-list" %}',
    vimmaApiAwsPowerLogList = '{% url "awspowerlog-list" %}',

    vimmaApiExpirationDetailRoot = '',
    vimmaApiFirewallRuleExpirationList = '',
    vimmaApiFirewallRuleList = '',
    vimmaEndpointCreateVM = '',
    vimmaEndpointPowerOnVM = '',
    vimmaEndpointPowerOffVM = '',
    vimmaEndpointRebootVM = '',
    vimmaEndpointDestroyVM = '',
    vimmaEndpointOverrideSchedule = '',
    vimmaEndpointChangeVMSchedule = '',
    vimmaEndpointSetExpiration = '',
    vimmaEndpointCreateFirewallRule = '',
    vimmaEndpointDeleteFirewallRule = '',

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

    vimmaProviders = JSON.parse('{{providers|escapejs}}'),

    _dummy_end;

function vmurl(vm, name, params) {
  return url(vm.content_type.app_label + name) + '?' + $.param(params);
}

function uriparams(uri, name) {
    name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"), results = regex.exec(uri);
    return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
}
