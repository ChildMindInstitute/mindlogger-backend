'use strict';
import models from '../models';
import s3Storage from '../services/s3';

let {User, Act, UserAct, Sequelize:{Op}} = models;
/**
 * Object for handle all auth request api
 */
let fileController = {
    /**
     * Fetch list of files
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next 
     * 
     */
    getList(req, res, next) {
        s3Storage.listPath(`images/${req.query.path || ''}`).then( contents => {
            let files = contents.map(content => content.Key)
            res.json({success:true, files})
        }).catch(err => {
            next(err)    
        })
    },

    postFile(req, res, next) {
        let bodyData= req.body
        if(bodyData.is_folder) {
            return s3Storage.newFolder(bodyData.path).then(result => {
                res.json({success: true, path: bodyData.path})
            }).catch(err => {
                next(err)
            })
        } else {
            res.json({success: true, file: req.files[0]})
        }
    },

    deleteFile(req,res, next) {
        let {path} = req.query
        s3Storage.deleteFile(path).then(result => {
            res.json({success: true})
        }).catch(err => {
            next(err)
        })
    }

}

export default fileController;