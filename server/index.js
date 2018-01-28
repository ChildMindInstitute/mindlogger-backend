'use strict';

import express from 'express';
import Bootstrap from './bootstrap';
import morgan from 'morgan'
let app = express();
app.use(morgan('dev'));
app.set('port', (process.env.PORT || 8000));
let bootstrap = new Bootstrap(app);
