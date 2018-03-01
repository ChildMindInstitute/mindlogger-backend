'use strict';
import models from '../models';

let {User, Answer, Act, Sequelize:{Op}} = models;
/**
 * Object for handle all auth request api
 */
let answerController = {
    /**
     * Handle login api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next 
     * 
     */
    getAnswers(req, res, next) {
        let query = {}
        if(req.params.userId) {
            query.user_id = req.params.userId
        }
        if(req.query.start_date) {
            query.createdAt = {
                [Op.gt]:new Date(req.query.start_date),
                [Op.lt]:new Date(req.query.end_date)
            }
        }
        Answer.findAndCountAll({ 
            where: query,
            include: [{ model: Act, as: 'act', required: true}, { model: User, as: 'user'}],
            order: [['updatedAt', 'DESC']],
            limit: parseInt(req.query.limit || 10),
            offset: parseInt(req.query.offset || 0)
        }).then(results => {
            res.json({ success: true, answers: results.rows, paging:{ total: results.count }, message: '' });
        }).catch(error => {
            next(error);
        });
    },

    getActsAndAnswers(req, res, next) {
        Act.findAll({ 
            include:[
                {
                    model: Answer,
                    as: 'answers',
                    where: req.params.userId ? {user_id: req.params.userId} : {},
                    order: [['updatedAt', 'DESC']],
                    required: true,
                }
            ],
        }).then(results => {
            res.json({ success: true, answered_acts: results, message: '' });
        }).catch(error => {
            next(error);
        });
    },

    addAnswer(req, res, next) {
        let {act_id, act_data, answer_data} = req.body
        Answer.create({
            user_id: req.user.id,
            act_id: act_id,
            act_data,
            answer_data
        }).then(result => {
            res.json({ success: true, answer: result, message: 'success'})
        }).catch(error => {
            next(error)
        })
    },
    getAnswer(req, res, next) {
        Answer.findOne({id: req.params.id}).then(result => {
            res.json({success: true, answer: result, message: 'success' })
        }).catch(error => {
            next(error)
        })
    },
    deleteAnswer(req, res, next) {
        Answer.destroy({where: {user_id: req.user.id, id: req.params.id}}).then(result => {
            res.json({ success: true, message: 'success'})
        }).catch(error => {
            next(error)
        })
    },

}

export default answerController;