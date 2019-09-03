girderTest.startApp();

describe('Test setApiRoot() function', function () {
    it('Check for default values and mutation', function () {
        waitsFor(function () {
            return $('.g-frontpage-body').length > 0;
        });

        runs(function () {
            // Test the default values.
            expect(girderformindlogger.rest.getApiRoot().slice(
                girderformindlogger.rest.getApiRoot().indexOf('/', 7))).toBe('/api/v1');

            var apiRootVal = '/foo/bar/v2';
            girderformindlogger.rest.setApiRoot(apiRootVal);
            expect(girderformindlogger.rest.getApiRoot()).toBe(apiRootVal);
        });
    });
});
