'use strict';
module.exports = (sequelize, DataTypes) => {
  var UserAct = sequelize.define('UserAct', {
    user_id: DataTypes.INTEGER,
    act_id: DataTypes.INTEGER
  });
  UserAct.associate = function(models) {
    // associations can be defined here
    UserAct.belongsTo(models.User, {foreignKey: 'user_id'})
    UserAct.belongsTo(models.Act, {foreignKey: 'act_id'})
  }
  return UserAct;
};