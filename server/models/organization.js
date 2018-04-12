'use strict';
module.exports = (sequelize, DataTypes) => {
  var organization = sequelize.define('organization', {
    name: DataTypes.STRING,
    industry: DataTypes.STRING,
    status: DataTypes.STRING,
    address: DataTypes.STRING,
    country: DataTypes.STRING,
    email: DataTypes.STRING,
    phone: DataTypes.STRING,
  }, { underscored: true});
  organization.associate = function(models) {
    organization.hasMany(models.Act);
    organization.hasMany(models.User);
  };
  organization.deleteOrganization = (organization) => {
    return organization.users.update({status: 'deleted'})
        .then(() => {
            return user.acts.update({status: 'deleted'});
        })
        .then(() => {
            return Organization.update({status: 'deleted'}, {where:{id: user.id}});
        })
        .then(() => {
            return true;
        })
}
  return organization;
};