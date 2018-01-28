'use strict';
var bcrypt = require('bcrypt');
module.exports = {
  up: (queryInterface, Sequelize) => {
    let hash = bcrypt.hashSync('password', 10)
    queryInterface.bulkInsert('Users', [{
      first_name: 'Admin',
      last_name: '',
      role: 'super_admin',
      email: 'admin@ab2cd.com',
      status: 'active', 
      password: hash,
      createdAt : new Date(),
      updatedAt : new Date(),
    }], {})
    if(process.env.NODE_ENV != 'production' ) {
      queryInterface.bulkInsert('Users', [{
        first_name: 'John',
        last_name: 'Doe',
        role: 'admin',
        email: 'tester@test.com',
        role: 'admin',
        status: 'active',
        password: hash,
        createdAt : new Date(),
        updatedAt : new Date(),
      }], {})
    }
    
    /*
      Add altering commands here.
      Return a promise to correctly handle asynchronicity.

      Example:
      return queryInterface.bulkInsert('Person', [{
        name: 'John Doe',
        isBetaMember: false
      }], {});
    */
  },

  down: (queryInterface, Sequelize) => {
    return queryInterface.bulkDelete('User', null, {});
    /*
      Add reverting commands here.
      Return a promise to correctly handle asynchronicity.

      Example:
      return queryInterface.bulkDelete('Person', null, {});
    */
  }
};
