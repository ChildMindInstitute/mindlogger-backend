'use strict';
import validator from 'validator';

export default {
    /**
     * Validate create user request
     * 
     * @param {any} req 
     * @param {any} res 
     * @param {any} next 
     */
    validateUser(req, res, next) {
        let bodyData = req.body;
        let errors = [];
        if (validator.isEmpty(bodyData.email || '')) {
            errors.push({ field: 'email', message: 'Email can not be blank.' });
        } else if (!validator.isEmail(bodyData.email)) {
            errors.push({ field: 'email', message: 'Invalid email address.' });
        }
        if (validator.isEmpty(bodyData.password || '')) {
            errors.push({ field: 'password', message: 'Password can not be blank.' });
        } else if (!validator.isLength(bodyData.password, { min: 8, max: 99 })) {
            errors.push({ field: 'password', message: 'Password length must be between 8 to 99.' });
        }

        if (errors.length) {
            res.status(400).json({ success: false, data: null, error: errors, message: 'Invalid request' });
        } else {
            next();
        }
    },

    /**
     * Validate reset password request
     * 
     * @param {any} req 
     * @param {any} res 
     * @param {any} next 
     */
    validateResetPassword(req, res, next) {
        let bodyData = req.body;
        let errors = [];
        if (validator.isEmpty(bodyData.token || '')) {
            errors.push({ field: 'token', message: 'Token can not be blank.' });
        }
        if (validator.isEmpty(bodyData.password || '')) {
            errors.push({ field: 'password', message: 'Password can not be blank.' });
        } else if (!validator.isLength(bodyData.password, { min: 8, max: 99 })) {
            errors.push({ field: 'password', message: 'Password length must be between 8 to 99.' });
        }

        if (errors.length) {
            res.status(400).json({ success: false, data: null, error: errors, message: 'Invalid request' });
        } else {
            next();
        }
    },

}
