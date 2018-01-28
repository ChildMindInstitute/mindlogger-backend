'use strict';

import { Router } from 'express';
import controllers from '../controllers';
import middleware from '../middleware';

let router = Router();
let {auth, answer} = controllers;
let validation = middleware.validation;
router.use(auth.checkUserAuthenticated);
router.get('/answers', answer.getAnswers);
router.post('/answers', answer.addAnswer);
router.get('/answers/:id', answer.getAnswer)

export default router;
