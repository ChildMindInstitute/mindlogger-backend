'use strict';

import nodemailer from 'nodemailer';
import config from '../config';

let smtpConfig = {
    host: config.mail.smtp.host,
    port: config.mail.smtp.port,
    secure: config.mail.smtp.isSecure,
    auth: {
        user: config.mail.smtp.user,
        pass: config.mail.smtp.password
    },
    tls: {
        rejectUnauthorized: false
    }
};
let transport = nodemailer.createTransport(smtpConfig);

export default {
    sendEmail(options) {
        let mailOptions = {
            from: config.mail.from_email,
            to: options.to,
            subject: options.subject,
            html: options.message
        };
        return transport.sendMail(mailOptions);
    }
}