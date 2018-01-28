'use strict';

import bodyParser from 'body-parser';
import cors from 'cors';
import compression from 'compression';
import methodOverride from 'method-override';
import passport from 'passport';
import helmet from 'helmet';
import express from 'express';
import schedule from 'node-schedule';
import routes from './routes';
import models from './models';
import config from './config';
//import scheduleJobs from './services/schedule-job';

/**
 * Application startup class
 * 
 * @export
 * @class Bootstrap
 */
export default class Bootstrap {

    /**
     * Creates an instance of Bootstrap.
     * @param {object} app 
     * 
     * @memberOf Bootstrap
     */
    constructor(app) {
        this.app = app;
        this.middleware();
        this.connectDb();
        this.routes();
        this.start();
        this.scheduleJobs();
    }

    /**
     * Load all middleware
     * @memberOf Bootstrap
     */
    middleware() {
        let app = this.app;
        app.use(cors());
        app.use(bodyParser.urlencoded({ extended: false }));
        app.use(bodyParser.json());
        app.use(compression());
        app.use(methodOverride());
        app.use(passport.initialize());
        app.use(helmet());
        app.use('assets', express.static(__dirname + '/uploads'));
    }

    /**
     * Check database connection
     * @memberOf Bootstrap
     */
    connectDb() {
        let sequelize = models.sequelize;
        return sequelize.authenticate().then(() => {
            console.log('Database connected successfully');
            return true;
        }).catch((error) => {
            console.log(`Database connection error %s`, error);
        });
    }

    /**
     * Load all routes
     * @memberOf Bootstrap
     */
    routes() {
        routes(this.app);
    }

    /**
     * Start express server
     * @memberOf Bootstrap
     */
    start() {
        let app = this.app;
        let port = app.get('port');
        app.listen(port, () => {
            console.log(`Server has started on port %d`, port);
        });
    }

    /**
     * Execute all schedule jobs
     * @memberOf Bootstrap
     */
    scheduleJobs() {        
        // let social_update_rule = config.schedule_jobs.social_account_update_time;       

        // let instagramSchedule = schedule.scheduleJob(social_update_rule, ()=> {
        //     scheduleJobs.instagramAccountUpdate();
        // });


    }


}