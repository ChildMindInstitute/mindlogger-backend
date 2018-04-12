'use strict';

import { Router } from 'express';
import controllers from '../controllers';
import middleware from '../middleware';

let router = Router();
let {auth, organization} = controllers;
let validation = middleware.validation;
router.use(auth.checkUserAuthenticated);
//router.get('/organizations/:id', answer.getOrganization);
router.get('/organizations', organization.getOrganizations);
router.post('/organizations', organization.addOrganization);

export default router;
