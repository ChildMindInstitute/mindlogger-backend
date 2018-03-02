'use strict';

import { Router } from 'express';
import controllers from '../controllers';
import middleware from '../middleware';
import { uploadImage } from '../services/s3';

let router = Router();
let {auth, file} = controllers;
let validation = middleware.validation;
router.use(auth.checkUserAuthenticated);
router.get('/files', file.getList);
router.post('/files', uploadImage.fields([{ name: 'file', maxCount: 1}]), file.postFile);

export default router;
