'use strict';
module.exports = {
  up: (queryInterface, Sequelize) => {
    return queryInterface.createTable('organizations', {
      id: {
        allowNull: false,
        autoIncrement: true,
        primaryKey: true,
        type: Sequelize.INTEGER
      },
      name: {
        type: Sequelize.STRING
      },
      industry: {
        type: Sequelize.STRING
      },
      address: {
        type: Sequelize.STRING
      },
      country: {
        type: Sequelize.STRING
      },
      phone: {
        type: Sequelize.STRING
      },
      email: {
        type: Sequelize.STRING
      },
      created_at: {
        allowNull: false,
        type: Sequelize.DATE
      },
      updated_at: {
        allowNull: false,
        type: Sequelize.DATE
      },
      status: {
        type: Sequelize.STRING,
        defaultValue: 'active'
      }
    }).then(res => {
      return [
        queryInterface.addColumn("users", "organization_id",{type: Sequelize.INTEGER}),
        queryInterface.addColumn("acts", "organization_id",{type: Sequelize.INTEGER})
      ];
    });
  },
  down: (queryInterface, Sequelize) => {
    return queryInterface.dropTable('organizations')
    .then(res => [queryInterface.removeColumn("users", "organization_id"), queryInterface.removeColumn("acts", "organization_id")]);
  }
};