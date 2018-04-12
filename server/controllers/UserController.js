'use strict';
import bcrypt from 'bcrypt';
import models from '../models';
import Email from '../services/email';
import {randomString} from '../services/utils'

let { User, Organization } = models;
/**
 * Object for handle all auth request api
 */
let userController = {
    getUsers(req, res, next) {
        let org = req.user.organization;
        let queryParam = org && { organization_id: org.id };
        User.findAndCountAll({ 
            where: queryParam,
            include: [
                {
                    model: Organization,
                    required: false,
                }
            ],
            order: [['created_at', 'DESC']],
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
        let password = req.body.password && req.body.password.length > 0 ? req.body.password : randomString(10)
        bcrypt.hash(password, 10).then(hash => {
            let userData = {
                email: req.body.email,
                password: hash,
                first_name: req.body.first_name,
                last_name: req.body.last_name,
                role: req.body.role,
                newsletter: req.body.newsletter,
            }
            if (req.body.organization_id) {
                userData.organization_id = req.body.organization_id;
            }
            return User.create(userData).then(newUser => {
                let user = Object.assign({}, newUser.get());
                delete user.password;
                user.password = password;
                return Email.addNewUser({email: userData.email, name: req.user.first_name + ' ' + req.user.last_name, password}).then(result => {
                    res.json({success: true, user: newUser, message:'New user created'});
                });
            })
        }).catch(error => {
            return next(error);
        });
    },

}

export default userController;