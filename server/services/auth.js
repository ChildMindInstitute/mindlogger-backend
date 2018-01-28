'use strict';

import passport from 'passport';
import LocalStrategy from 'passport-local';
import bcrypt from 'bcrypt';
import models from '../models';

let User = models.User;
let signupLocalStrategy = new LocalStrategy({
    usernameField: 'email',
    passReqToCallback: true,
}, (req, username, password, done) => {
    
    User.findOne({
        where: { email: username }
    }).then(data => {
        let user = data ? data.get() : null;
        if (user) {
            let error = new Error('Email already exists');
            error.name = 'EMAIL_EXISTS';
            return done(error, false);
        } else {
            bcrypt.hash(password, 10).then(hash => {
                let userData = {
                    email: username,
                    password: hash,
                    first_name: req.body.first_name,
                    last_name: req.body.last_name,
                    role: req.body.role,
                    newsletter: req.body.newsletter
                }
                User.create(userData).then(newUser => {
                    let user = Object.assign({}, newUser.get());
                    delete user.password;
                    return done(null, user || false);
                }).catch(error => {
                    return done(error, false);
                });
            }).catch(error => {
                return done(error, false);
            });
        }
    }).catch(error => {
        return done(error, false);
    });

    //return done(null, {});
});

let loginLocalStrategy = new LocalStrategy({
    usernameField: 'email',
    passReqToCallback: true,
}, (req, username, password, done) => {
    User.findOne({
        where: { email: username }
    }).then(data => {
        let user = data ? data.get() : null;
        if (user) {
            bcrypt.compare(password, user.password).then(res => {
                if (res) {
                    if(user.status == 'active') {
                        delete user.password;
                        return done(null, user);
                    } else {
                        let error = new Error('Email is not confirmed');
                        return done(error, false);
                    }
                    
                } else {
                    let error = new Error('Invalid email or password');
                    return done(error, false);
                }
            }).catch(error => {
                return done(error, false);
            });
        } else {
            let error = new Error('Invalid email or password');
            return done(error, false);
        }
    }).catch(error => {
        return done(error, false);
    });

});


passport.use('signup', signupLocalStrategy);
passport.use('login', loginLocalStrategy);

passport.serializeUser((user, done) => {
    let createAccessToken = () => {
        let token = User.generateToken();
        User.findOne({ where: { access_token: token }, attributes: ['access_token'] }).then(data => {
            let existingUser = data ? data.get() : null;
            if (existingUser) {
                createAccessToken();
            } else {
                User.update({ access_token: token }, { where: { id: user.id } }).then(afftectedRows => {
                    user.access_token = token;
                    return done(null, token);
                }).catch(error => {
                    return done(error, false);
                });
            }
        }).catch(error => {
            return done(error, false);
        });;
    };

    if (user && user.id) {
        createAccessToken();
    }
});

passport.deserializeUser((token, done) => {
    User.findOne({ where: { access_token: token } }).then(data => {
        let user = data ? data.get() : null;
        return done(error, user);
    }).then(error => {
        return done(error, false);
    });;
});