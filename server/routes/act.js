'use strict';

import { Router } from 'express';
import controllers from '../controllers';
import middleware from '../middleware';
import s3Storage from '../services/s3';

let router = Router();
let {auth, act} = controllers;
let validation = middleware.validation;
let uploadFile = s3Storage.uploadFile();
let uploadImage = s3Storage.uploadImage();
router.use(auth.checkUserAuthenticated);
router.get('/users/:id/assigned_acts', act.getAssignedActs);
router.get('/acts/search', act.searchActs)
router.put('/users/:userId/assign/:actId', act.assignAct)
router.get('/acts', act.getActs);

router.post('/acts', uploadFile.fields([{ name: 'audio', maxCount: 1}, { name: 'image', maxCount: 1}]) , act.addAct);
router.put('/acts/:id', uploadFile.fields([{ name: 'audio', maxCount: 1}, { name: 'image', maxCount: 1}]), act.updateAct);
router.delete('/acts/:id', act.deleteAct);
export default router;
