'use strict';

import { Router } from 'express';
import controllers from '../controllers';
import middleware from '../middleware';
import s3Storage from '../services/s3';

let router = Router();
let {auth, file} = controllers;
let validation = middleware.validation;
let uploadImage = s3Storage.uploadImage();
router.use(auth.checkUserAuthenticated);
router.get('/files', file.getList);
router.post('/files', uploadImage.fields([{ name: 'file', maxCount: 1}]), file.postFile);
router.delete('/files', file.deleteFile);
export default router;
