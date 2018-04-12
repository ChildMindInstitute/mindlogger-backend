'use strict';

module.exports = {
  up: (queryInterface, Sequelize) => {
    return [
      queryInterface.addColumn("answers", "platform",{type: Sequelize.STRING}),
      queryInterface.addColumn("answers", "score",{type: Sequelize.FLOAT})
    ];
  },

  down: (queryInterface, Sequelize) => {
    return [
      queryInterface.removeColumn("answers","platform"),
      queryInterface.removeColumn("answers","score")
    ];
  }
};
