'use strict';

import { Router } from 'express';
import auth from './auth';
import act from './act';
import answer from './answer';
let router = new Router();

let register = app => {
    router.use('/api', [auth, act, answer]);
    router.use('/', (req, res) => {
        res.send('Backend service for the AB2CD platform.');
    });
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
