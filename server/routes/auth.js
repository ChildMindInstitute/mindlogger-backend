'use strict';

import { Router } from 'express';
import controllers from '../controllers';
import middleware from '../middleware';

let router = Router();
let auth = controllers.auth;
let validation = middleware.validation;

router.post('/login', auth.login);
router.post('/user', validation.validateUser, auth.signup);
router.put('/user', auth.checkUserAuthenticated, auth.update);
router.post('/user/change-password', auth.checkUserAuthenticated, auth.changePassword);
router.post('/user/forgot-password', auth.forgotPassword);
router.post('/user/reset-password', validation.validateResetPassword, auth.resetPassword);
router.delete('/user', auth.checkUserAuthenticated, auth.logout);
router.delete('/user/delete', auth.checkUserAuthenticated, auth.deleteUser, auth.logout);

export default router;
