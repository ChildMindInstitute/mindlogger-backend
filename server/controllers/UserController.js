'use strict';
import bcrypt from 'bcrypt';
import models from '../models';
import Email from '../services/email';
import {randomString} from '../services/utils'

let {User} = models;
/**
 * Object for handle all auth request api
 */
let userController = {
    getUsers(req, res, next) {
        User.findAndCountAll({ 
            order: [['createdAt', 'DESC']],
            limit: parseInt(req.query.limit || 10),
            offset: parseInt(req.query.offset || 0)
        }).then(results => {
            console.log(results)
            res.json({ success: true, users: results.rows, paging:{ total: results.count }, message: '' });
        }).catch(error => {
            next(error);
        });
    },
    
    inviteUser(req, res, next) {
        const password = randomString(10)
        bcrypt.hash(password, 10).then(hash => {
            let userData = {
                email: req.body.email,
                password: hash,
                first_name: req.body.first_name,
                last_name: req.body.last_name,
                role: req.body.role,
                newsletter: req.body.newsletter
            }
            User.create(userData).then(newUser => {
                let user = Object.assign({}, newUser.get());
                delete user.password;
                return Email.addNewUser({email: userData.email, name: req.user.first_name + ' ' + req.user.last_name, password});
            }).catch(error => {
                next(error)
            });
            
        }).catch(error => {
            return next(error);
        });
    },

}

export default userController;