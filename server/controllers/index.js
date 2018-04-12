'use strict';

import auth from './AuthController';
import user from './UserController';
import act from './ActController';
import answer from './AnswerController';
import organization from './OrganizationController';
import file from './FileController';
let controllers = { auth, act, answer, user, file, organization };

export default controllers;
