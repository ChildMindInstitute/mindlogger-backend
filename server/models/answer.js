'use strict';
module.exports = (sequelize, DataTypes) => {
  var Answer = sequelize.define('answer', {
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
    platform: DataTypes.STRING,
    score: DataTypes.FLOAT,
  }, {underscored: true});
  Answer.associate = function(models) {
    // associations can be defined here
    Answer.belongsTo(models.User)
    Answer.belongsTo(models.Act)
  }
  return Answer;
};