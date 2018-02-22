'use strict';
module.exports = (sequelize, DataTypes) => {
  var Act = sequelize.define('Act', {
    title: DataTypes.STRING,
    type: DataTypes.STRING,
    act_data: {
      type: DataTypes.TEXT,
      get() {
          return JSON.parse(this.getDataValue('act_data') || "{}");
      },
      set(value) {
          this.setDataValue('act_data', JSON.stringify(value || {}));
      },
    },
    status:{
      type: DataTypes.STRING, 
      defaultValue:'active'
    }
  },{
    defaultScope: {
      where: {
        status: 'active'
      }
    }
  });
  Act.associate = function(models) {
    // associations can be defined here
    Act.belongsTo(models.User, {as: 'author', foreignKey:'user_id'})
    Act.hasMany(models.UserAct, {foreignKey:'act_id'})
    Act.belongsToMany(models.User, {through: 'UserAct', foreignKey:'act_id'})
    Act.hasMany(models.Answer, { as: 'answers', foreignKey:'act_id'})
  }
  return Act;
};