var indexUrl = '{% url "index" %}',

    vimmaApiRoot = '{% url "api-root" %}',
    vimmaApiScheduleList = '{% url "schedule-list" %}',
    vimmaApiScheduleDetailRoot = apiDetailRootUrl(
            '{% url "schedule-detail" 0 %}'),
    vimmaApiTimeZoneList = '{% url "timezone-list" %}',
    vimmaApiProjectList = '{% url "project-list" %}',
    vimmaApiProjectDetailRoot = apiDetailRootUrl(
            '{% url "project-detail" 0 %}'),
    vimmaApiProfileList = '{% url "profile-list" %}',
    vimmaApiProfileDetailRoot = apiDetailRootUrl(
            '{% url "profile-detail" 0 %}'),
    vimmaApiUserList = '{% url "user-list" %}',
    vimmaApiUserDetailRoot = apiDetailRootUrl(
            '{% url "user-detail" 0 %}'),
    vimmaApiVMList = '{% url "vm-list" %}',
    vimmaApiVMDetailRoot = apiDetailRootUrl(
            '{% url "vm-detail" 0 %}'),
    vimmaApiDummyVMDetailRoot = apiDetailRootUrl(
            '{% url "dummyvm-detail" 0 %}'),
    vimmaApiAWSVMDetailRoot = apiDetailRootUrl(
            '{% url "awsvm-detail" 0 %}'),
    vimmaApiProviderList = '{% url "provider-list" %}',
    vimmaApiProviderDetailRoot = apiDetailRootUrl(
            '{% url "provider-detail" 0 %}'),
    vimmaApiVMConfigList = '{% url "vmconfig-list" %}',
    vimmaApiAuditList = '{% url "audit-list" %}',

    vimmaEndpointCreateVM = '{% url "createVM" %}',
    vimmaEndpointPowerOnVM = '{% url "powerOnVM" %}',
    vimmaEndpointPowerOffVM = '{% url "powerOffVM" %}',
    vimmaEndpointRebootVM = '{% url "rebootVM" %}',
    vimmaEndpointDestroyVM = '{% url "destroyVM" %}',
    vimmaEndpointOverrideSchedule = '{% url "overrideSchedule" %}',
    vimmaEndpointChangeVMSchedule = '{% url "changeVMSchedule" %}',

    vimmaUserId = {{ user.id }},

    restPaginateByParam = '{{settings.REST_FRAMEWORK.PAGINATE_BY_PARAM|escapejs}}',
    restMaxPaginateBy = {{settings.REST_FRAMEWORK.MAX_PAGINATE_BY}},

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

    _dummy_end;