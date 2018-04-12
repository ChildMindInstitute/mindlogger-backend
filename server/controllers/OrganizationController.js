'use strict';
import models from '../models';

let {Organization, Sequelize:{Op}} = models;
/**
 * Object for handle all auth request api
 */
let organizationController = {
    /**
     * Handle login api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next 
     * 
     */
    getOrganizations(req, res, next) {
        let param = {
            order: [['updated_at', 'DESC']],
        }
        if (req.user.role != 'super_admin') {
            next(new Error("Only super admin can authorized"));
        }
        Organization.findAndCountAll({}).then(results => {
            res.json({ success: true, organizations: results.rows, paging:{ total: results.count }, message: '' });
        }).catch(error => {
            next(error);
        });
    },
    addOrganization(req, res, next) {
        let {name} = req.body
        Organization.create({
            name,
        }).then(result => {
            console.log(result)
            res.json({ success: true, organization: result, message: 'success'});
        }).catch(error => {
            next(error);
        })
    },

    deleteOrganization(req, res, next) {
        let params = { id: req.params.id}
        if(req.user.role != 'super_admin') {
            next(error);
        }
        Act.update({status: 'inactive'},{where: params}).then(result => {
            res.json({ success: true, message: 'success'});
        }).catch(error => {
            next(error);
        })
    },

}

export default organizationController;