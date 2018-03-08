'use strict';

module.exports = {
  up: (queryInterface, Sequelize) => {
    return [
      queryInterface.addColumn("Answers", "platform",{type: Sequelize.STRING}),
      queryInterface.addColumn("Answers", "score",{type: Sequelize.FLOAT})
    ];
  },

  down: (queryInterface, Sequelize) => {
    return [
      queryInterface.removeColumn("Answers","platform"),
      queryInterface.removeColumn("Answers","score")
    ];
  }
};
