'use strict';

import { Router } from 'express';
import controllers from '../controllers';
import middleware from '../middleware';

let router = Router();
let {auth, act} = controllers;
let validation = middleware.validation;
router.use(auth.checkUserAuthenticated);
router.get('/users/:id/assigned_acts', act.getAssignedActs);
router.get('/acts/search', act.searchActs)
router.put('/users/:userId/assign/:actId', act.assignAct)
router.get('/acts', act.getActs);

router.post('/acts', act.addAct);
router.put('/acts/:id', act.updateAct);
router.delete('/acts/:id', act.deleteAct);
export default router;
