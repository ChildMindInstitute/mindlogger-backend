'use strict';
import models from '../models';

let {User, Act} = models;
/**
 * Object for handle all auth request api
 */
let actController = {
    /**
     * Handle login api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next 
     * 
     */
    getActs(req, res, next) {
        Act.findAndCountAll({ 
            where: {user_id: req.user.id},
            order: [['updatedAt', 'DESC']],
            limit: parseInt(req.query.limit || 10),
            offset: parseInt(req.query.offset || 0)
        }).then(results => {
            res.json({ success: true, acts: results.rows, paging:{ total: results.count }, message: '' });
        }).catch(error => {
            next(error);
        });
    },

    getAssignedActs(req, res, next) {
        let user = req.user
        user.getActs().then(results => {
            console.log(results)
            res.json({ success: true, acts: results, message: '' });
        }).catch(error => {
            next(error);
        })
    },

    addAct(req, res, next) {
        let {title, type, act_data} = req.body
        Act.create({
            user_id: req.user.id,
            title,
            type,
            act_data
        }).then(result => {
            console.log(result)
            res.json({ success: true, act: result, message: 'success'})
        }).catch(error => {
            next(error)
        })
    },

    updateAct(req, res, next) {
        let {title, act_data} = req.body
        Act.update({ act_data, title }, { where:{user_id: req.user.id, id: req.params.id} }).then(result => {
            res.json({ success: true, act: result, message: 'success'})
        }).catch(error => {
            next(error)
        })
    },

    deleteAct(req, res, next) {
        Act.destroy({where: {user_id: req.user.id, id: req.params.id}}).then(result => {
            res.json({ success: true, message: 'success'})
        }).catch(error => {
            next(error)
        })
    },

}

export default actController;