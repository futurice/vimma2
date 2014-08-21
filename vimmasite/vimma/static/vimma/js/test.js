QUnit.test('apiDetailRootUrl', function(assert) {
    assert.strictEqual(apiDetailRootUrl('api/MyObject/0/'), 'api/MyObject/');
});

QUnit.test('clone model', function(assert) {
    assert.strictEqual(clone(null), null);
    assert.strictEqual(clone(undefined), undefined);
    assert.strictEqual(clone(3), 3);
    assert.strictEqual(clone(true), true);
    assert.strictEqual(clone(false), false);
    assert.strictEqual(clone(''), '');
    assert.strictEqual(clone('john'), 'john');

    assert.deepEqual(clone([]), []);
    assert.deepEqual(clone([8]), [8]);
    assert.deepEqual(clone([8, 'apple']), [8, 'apple']);

    assert.deepEqual(clone({}), {});
    assert.deepEqual(clone({item: 'apples'}), {item: 'apples'});
    (function() {
        var x = {a: 5, b: {name: 'John'}};
        var y = clone(x);
        assert.deepEqual(x, y);
        // check that y.b points to a different object than x.b
        assert.notStrictEqual(x.b, y.b);
    })();

    assert.deepEqual({items: [{name: 'chocolate'}, 'milk']},
                     {items: [{name: 'chocolate'}, 'milk']});
    assert.deepEqual({a: 3, b: '4'}, {b: '4', a: 3});
});

QUnit.test('sameModels()', function(assert) {
    assert.strictEqual(true, sameModels(null, null));
    assert.strictEqual(true, sameModels(undefined, undefined));
    assert.strictEqual(true, sameModels('', ''));
    assert.strictEqual(true, sameModels('apple', 'apple'));
    assert.strictEqual(true, sameModels(5, 5));
    assert.strictEqual(true, sameModels([], []));
    assert.strictEqual(true, sameModels(
            [{who: 'me', where: ['beach', 'water']}],
            [{where: ['beach', 'water'], who: 'me'}]));

    assert.strictEqual(false, sameModels(null, undefined));
    assert.strictEqual(false, sameModels('5', 5));
    assert.strictEqual(false, sameModels({who: 5}, {who: '5'}));
    assert.strictEqual(false, sameModels({}, {a: 1}));
    assert.strictEqual(false, sameModels({a: 1}, {}));
    assert.strictEqual(false, sameModels({a: 1}, {b: 1}));
    assert.strictEqual(false, sameModels({a: 1}, {a: 2}));
    assert.strictEqual(false, sameModels(['a'], []));
    assert.strictEqual(false, sameModels([], ['a']));
    assert.strictEqual(false, sameModels(['a'], ['b']));
    assert.strictEqual(false, sameModels(['3'], [3]));
});
