'use strict';

import { Router } from 'express';
import controllers from '../controllers';
import middleware from '../middleware';

let router = Router();
let {auth, answer} = controllers;
let validation = middleware.validation;
router.use(auth.checkUserAuthenticated);
router.get('/users/:userId/answers', answer.getAnswers);
router.get('/users/:userId/answered_acts', answer.getActsAndAnswers);
router.post('/answers', answer.addAnswer);
router.get('/answers/:id', answer.getAnswer)

export default router;
