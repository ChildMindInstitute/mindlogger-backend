'use strict';

import { Router } from 'express';
import controllers from '../controllers';
import middleware from '../middleware';

let router = Router();
let {auth, user} = controllers;
let validation = middleware.validation;
router.use(auth.checkUserAuthenticated);
router.get('/users', user.getUsers);
router.post('/invite_user', user.inviteUser);
//router.get('/users/:id', user.getUser);
export default router;
