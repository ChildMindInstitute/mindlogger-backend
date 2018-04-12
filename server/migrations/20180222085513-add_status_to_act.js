'use strict';

module.exports = {
  up: (queryInterface, Sequelize) => {
    return queryInterface.addColumn("acts", "status",{type: Sequelize.STRING, defaultValue: 'active'});
  },

  down: (queryInterface, Sequelize) => {
    return queryInterface.removeColumn("acts","status");
  }
};
