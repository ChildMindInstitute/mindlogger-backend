'use strict';
import models from '../models';

let {User, Act, UserAct, Sequelize:{Op}} = models;
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
        Act.findAll({
            include: [{
                model: UserAct,
                where:{user_id: req.params.id}
            }]
        }).then(results => {
            console.log(results)
            res.json({ success: true, assigned_acts: results, message: '' });
        }).catch(error => {
            next(error);
        })
    },

    searchActs(req, res, next) {
        let {keyword, limit, offset} = req.query
        var whereParam = {}
        if(keyword && keyword.length>0) {
            whereParam = {
                [Op.or]: [
                    {id:keyword},
                    {title:{
                        [Op.like]: `%${keyword}%`
                    }}]
            }
        }
        Act.findAndCountAll({
            where: whereParam,
            order:[['updatedAt', 'DESC']],
            limit: parseInt(limit || 10),
            offset: parseInt(offset || 0),
        }).then(results => {
            res.json({ success: true, acts: results.rows, paging: {total: results.count}})
        }).catch(error => {
            next(error);
        })
    },

    assignAct(req, res, next) {
        let {userId, actId} = req.params
        if (req.query.is_delete) {
            UserAct.destroy({where: {user_id: userId, act_id: actId}}).then( result => {
                res.json({ success: true, message: 'success'})
            }).catch(error => {
                next(error)
            })
        } else {
            UserAct.find({where:{user_id: userId, act_id: actId}, defaults: {}}).then( result => {
                if (result){
                    return result
                } else {
                    return UserAct.create({user_id: userId, act_id: actId})
                }
            }).then(result => {
                res.json({success: true, message: 'success'})
            }).catch( error => {
                next(error)
            })
        }
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
        let params = { id: req.params.id}
        if(req.user.role != 'super_admin') {
            params.user_id = req.user.id;
        }
        Act.update({status: 'inactive'},{where: params}).then(result => {
            res.json({ success: true, message: 'success'})
        }).catch(error => {
            next(error)
        })
    },

}

export default actController;