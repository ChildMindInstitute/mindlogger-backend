'use strict';

module.exports = {
  up: (queryInterface, Sequelize) => {
    return queryInterface.addColumn("Acts", "status",{type: Sequelize.STRING, defaultValue: 'active'});
  },

  down: (queryInterface, Sequelize) => {
    return queryInterface.removeColumn("Acts","status");
  }
};
