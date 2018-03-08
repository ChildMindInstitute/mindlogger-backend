'use strict';

module.exports = {
  up: (queryInterface, Sequelize) => {
    /*
      Add altering commands here.
      Return a promise to correctly handle asynchronicity.

      Example:
      return queryInterface.createTable('users', { id: Sequelize.INTEGER });
    */
    let ar = []
    ar.push(
      queryInterface.sequelize.query('UPDATE "Users" SET role=\'admin\' where role = \'clinician\''),
      queryInterface.sequelize.query('UPDATE "Users" SET role=\'user\' where role = \'patient\'')
    )
    return Promise.all(ar)
  },

  down: (queryInterface, Sequelize) => {
    /*
      Add reverting commands here.
      Return a promise to correctly handle asynchronicity.

      Example:
      return queryInterface.dropTable('users');
    */
    let ar = []
    ar.push(
      queryInterface.sequelize.query('UPDATE "Users" SET role=\'clinician\' where role = \'admin\''),
      queryInterface.sequelize.query('UPDATE "Users" SET role=\'patient\' where role = \'user\'')
    )
    return Promise.all(ar)
  }
};
