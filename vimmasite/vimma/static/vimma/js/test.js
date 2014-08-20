QUnit.test('apiDetailRootUrl', function(assert) {
    assert.strictEqual(apiDetailRootUrl('api/MyObject/0/'), 'api/MyObject/');
});
