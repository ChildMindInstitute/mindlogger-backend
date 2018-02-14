'use strict';

import express, { Router } from 'express';
import path from 'path';
import auth from './auth';
import act from './act';
import answer from './answer';
import user from './user';
let router = new Router();

let register = app => {
    router.use('/api', [auth, act, answer, user]);
    router.use(express.static(path.join(__dirname, '../../client/build')));
    app.use(router);
    app.use((req,res,next)=> {
        let error =new Error('Not Found');
        error.status = 404;
        next(error);
    });
    app.use((error, req, res, next) => {
        res.status(error.status || 500).json({success: false, data: null, error, message: error.message})
    });
}

export default register;
