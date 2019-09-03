/**
 * Expose the symbols for a girderformindlogger plugin under the window.girderformindlogger.plugins
 * namespace. Required since each plugin is loaded dynamically.
 */
var registerPluginNamespace = function (pluginName, symbols) {
    window.girderformindlogger.plugins[pluginName] = symbols;
};

export {
    registerPluginNamespace
};
