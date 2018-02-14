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
    app.use((error, req, res, next) => {
        res.status(error.status || 500).json({success: false, data: null, error, message: error.message})
    });

    app.get('*', (req,res) => {
        res.sendFIle(path.join(__dirname, '../../client/build/index.html'))
    })
}

export default register;
