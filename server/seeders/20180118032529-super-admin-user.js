'use strict';
var bcrypt = require('bcrypt');
module.exports = {
  up: (queryInterface, Sequelize) => {
    let hash = bcrypt.hashSync('admin2mindlogger', 10)
    return queryInterface.bulkInsert('users', [{
      first_name: 'Super Admin',
      last_name: '',
      role: 'super_admin',
      email: 'admin@mindlogger.org',
      status: 'active',
      password: hash,
      created_at : new Date(),
      updated_at : new Date()
    }], {}).then( res => {
      if(process.env.NODE_ENV != 'production' ) {
        return queryInterface.bulkInsert('Users', [{
          first_name: 'John',
          last_name: 'Doe',
          role: 'admin',
          email: 'tester@test.com',
          role: 'admin',
          status: 'active',
          password: hash,
          created_at : new Date(),
          updated_at : new Date(),
        }], {})
      } else {
        return true;
      }
    });
    
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
