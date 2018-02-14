'use strict';
module.exports = (sequelize, DataTypes) => {
  var Answer = sequelize.define('Answer', {
    act_id: DataTypes.INTEGER,
    user_id: DataTypes.INTEGER,
    act_data: {
      type: DataTypes.TEXT,
      get() {
          return JSON.parse(this.getDataValue('act_data') || "{}");
      },
      set(value) {
          this.setDataValue('act_data', JSON.stringify(value || {}));
      },
    },
    answer_data: {
      type: DataTypes.TEXT,
      get() {
          return JSON.parse(this.getDataValue('answer_data') || "{}");
      },
      set(value) {
          this.setDataValue('answer_data', JSON.stringify(value || {}));
      },
    },
  });
  Answer.associate = function(models) {
    // associations can be defined here
    Answer.belongsTo(models.User,{as: 'user', foreignKey: 'user_id'})
    Answer.belongsTo(models.Act, { as: 'act', foreignKey:'act_id'})
  }
  return Answer;
};