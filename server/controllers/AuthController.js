'use strict';
import passport from 'passport';
import bcrypt from 'bcrypt';
import passportService from '../services/auth';
import models from '../models';
import Email from '../services/email';

let {User} = models;
/**
 * Object for handle all auth request api
 */
let authController = {
    /**
     * Handle login api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next 
     * 
     */
    login(req, res, next) {
        passport.authenticate('login', (error, user, info) => {
            if (error) {
                error.status = 400;
                next(error);
            } else {
                req.logIn(user, error => {
                    if (error) {
                        error.status = 400;
                        next(error);
                    } else {
                        console.log(user)
                        res.json({ success: true, user, message: '' });
                    }
                });
            }
        })(req, res, next);
    },

    /**
     * Handle signup api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next  
     * 
     */
    signup(req, res, next) {
        passport.authenticate('signup', (error, user, info) => {
            if (error) {
                error.status = 400;
                if (error.name === 'EMAIL_EXISTS') {
                    res.status(400).json({ success: false, error: [{ field: 'email', message: 'Email already exists.' }], message: 'Invalid request' });
                } else {
                    next(error);
                }
            } else {
                if (user) {
                    res.status(200).json({ success: true, user: user, message: 'User created successfully' });
                } else {
                    res.status(400).json({ success: true, user: user, message: 'User not created' });
                }
            }
        })(req, res, next);
    },

    /**
     * Handle logout api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next 
     * 
     */
    logout(req, res, next) {
        User.find({ where: { id: req.user.id } }).then(user => {
            if (user) {
                user.updateAttributes({
                    access_token: ''
                }).then(data => {
                    res.status(200).json({ success: true, message: 'User has been logout successfully' });
                }).catch(error => {
                    next(error);
                });
            } else {
                let error = new Error('Bad request');
                error.status = 400;
                next(error);
            }
        }).catch(error => {
            next(error);
        });
    },

    /**
     * Handle change password api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next 
     * 
     */
    changePassword(req, res, next) {
        User.find({
            where: { id: req.user.id }
        }).then(data => {
            let user = data ? data.get() : null;
            let bodyData = {
                current_password: req.body.current_password || '',
                new_password: req.body.new_password || ''
            }
            if (user) {
                bcrypt.compare(bodyData.current_password, user.password).then(result => {
                    if (result) {
                        bcrypt.hash(bodyData.new_password, 10).then(hash => {
                            let userData = {
                                password: hash
                            }
                            data.updateAttributes(userData).then(data => {
                                res.status(200).json({ success: true, message: 'Password has been changed successfully' });
                            }).catch(error => {
                                return next(error);
                            });
                        }).catch(error => {
                            return next(error);
                        });
                    } else {
                        let error = new Error("Current password doesn't match");
                        error.status = 400;
                        return next(error);
                    }
                }).catch(error => {
                    return next(error);
                });
            } else {
                let error = new Error('User is not authenticated');
                error.status = 401;
                return next(error);
            }
        }).catch(error => {
            return next(error);
        });
    },

    /**
     * Handle forgot password api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next  
     * 
     */
    forgotPassword(req, res, next) {
        let email = req.body.email || false;
        let token = User.generateTempToken();
        if (email) {
            User.find({ where: { email: email } }).then(user => {
                if (user) {
                    return user.updateAttributes({ verify_token: token }).then(data => {
                        let options = {
                            to: user.email,
                            firstName: user.first_name,
                            token
                        };
                        return Email.forgotPassword(options);
                    }).then(result => {
                        res.status(200).json({ success: true, message: 'Reset password link has been sent on your email.' });
                    }).catch(error => {
                        next(error);
                    });
                } else {
                    let error = new Error("Email doesn't exist.");
                    error.status = 400;
                    next(error);
                }
            }).catch(error => {
                next(error);
            });
        } else {
            let error = new Error('Bad request');
            error.status = 400;
            next(error);
        }
    },

    /**
     * Handle reset password api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next  
     * 
     */
    resetPassword(req, res, next) {
        let password = req.body.password || false;
        let token = req.body.token || false;
        if (token && passport) {
            User.find({ where: { verify_token: token } }).then(user => {
                if (user) {
                    let options = {
                        to: user.email
                    };
                    bcrypt.hash(password, 10).then(hash => {
                        let userData = {
                            password: hash,
                            verify_token: ''
                        };   
                        return user.updateAttributes(userData);
                    }).then(data => {
                        return Email.thankYouResetPassword(options);
                    }).then( result => {
                        res.status(200).json({ success: true, message: 'Password has been reset successfully' });
                    }).catch(error => {
                        return next(error);
                    });

                } else {
                    let error = new Error("Token doesn't exist.");
                    error.status = 400;
                    next(error);
                }
            }).catch(error => {
                next(error);
            });
        } else {
            let error = new Error('Bad request');
            error.status = 400;
            next(error);
        }
    },

    /**
     * Handle update user api request
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next  
     * 
     */
    update(req, res, next) {
        User.find({ where: { id: req.user.id } }).then(user => {
            if (user) {
                let data = {
                    first_name: req.body.first_name,
                    last_name: req.body.last_name,
                    role: req.body.role,
                }
                user.updateAttributes(data).then(data => {
                    let updatedUser = Object.assign({}, data.get());
                    delete updatedUser.password;
                    res.status(200).json({ success: true, user: updatedUser, message: 'User updated successfully' });
                }).catch(error => {
                    next(error);
                });
            } else {
                let error = new Error('Bad request');
                error.status = 400;
                next(error);
            }
        }).catch(error => {
            next(error);
        });
    },

    /**
     * Check user id exists
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next  
     * 
     */
    checkUserExist(req, res, next) {
        let userId = req.params.id;
        if (userId && userId > 0) {
            User.findById(userId).then(user => {
                if (user) {
                    return next();
                } else {
                    let error = new Error('Page not found');
                    error.status = 404;
                    next(error);
                }
            }).catch(error => {
                next(error);
            });
        } else {
            let error = new Error('Page not found');
            error.status = 404;
            next(error);
        }
    },

    /**
     * Check user authentication
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next  
     * 
     */
    checkUserAuthenticated(req, res, next) {
        let token = getToken(req);
        if (token) {
            return User.find({ where: { access_token: token } }).then(user => {
                if (!user) {
                    let error = new Error('Invalid access token');
                    error.status = 401;
                    next(error);
                } else {
                    req.user = user;
                    return next(null, user, { scope: 'all' });
                }
            }).catch(error => {
                next(error);
            });
        } else {
            let error = new Error('User is not authenticated.');
            error.status = 401;
            next(error);
        }
    },

    /**
     * Delete user
     * 
     * @param {object} req 
     * @param {object} res 
     * @param {object} next  
     * 
     */
    deleteUser(req, res, next) {
        let user = req.user;
        User.deleteUser(user)
        .then(() => {
            res.status(200).json({ success: true, message: 'User deleted successfully' });
        }).catch( error => {
            next(error);
        });
    }
}

let getToken = (req) => {
    let token;
    if (req.headers && req.headers.access_token) {
        token = req.headers.access_token;
    }

    if (req.body && req.body.access_token) {
        token = req.body.access_token;
    }

    if (req.query && req.query.access_token) {
        token = req.query.access_token;
    }

    if (req.query && req.params.access_token) {
        token = req.params.access_token;
    }
    return token;
}

export default authController;