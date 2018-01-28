'use strict';
import models from '../models';

let {User, Answer, Act} = models;
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
        Answer.findAndCountAll({ 
            where: {user_id: req.user.id},
            order: [['updatedAt', 'DESC']],
            limit: parseInt(req.query.limit || 10),
            offset: parseInt(req.query.offset || 0)
        }).then(results => {
            res.json({ success: true, answers: results.rows, paging:{ total: results.count }, message: '' });
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
        Answer.findOne({id: req.params.id}).then(res => {
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