'use strict';
module.exports = (sequelize, DataTypes) => {
  var UserAct = sequelize.define('user_act', {
    user_id: DataTypes.INTEGER,
    act_id: DataTypes.INTEGER
  }, {underscored: true});
  UserAct.associate = function(models) {
    // associations can be defined here
    UserAct.belongsTo(models.User, {foreignKey: 'user_id'})
    UserAct.belongsTo(models.Act, {foreignKey: 'act_id'})
  }
  return UserAct;
};