'use strict';

import emailer from './base-emailer';
import config from '../config';

export default {
    forgotPassword(data) {
        let message = `Hi ${data.firstName}, <br/>
 Sorry to hear you’re having trouble logging into Big Spaghetti.
 We can help you get right back into your account. 
 <a href="${config.app.basePath}/reset-password?token=${data.token}">Click here</a> to reset your Big Spaghetti password.`;
        let options = {
            to: data.to,
            subject: 'Forgot Password',
            message
        }
        return emailer.sendEmail(options);
    },

    thankYouResetPassword(data) {
        let message = `Thanks for visiting <a href="${config.app.basePath}">bigspaghetti.com!</a> Per your request, we have successfully changed your password.<br/> 
 If you need to contact us for any reason, please feel free to get in touch.`;
        let options = {
            to: data.to,
            subject: 'Password Updated',
            message
        }
        return emailer.sendEmail(options);
    },

    remindNewMessage(data) {
        let message = `<p>${data.name} wants to work with you!<br/> <a href="${config.app.basePath}">Check your messages now.</a></p>`;
        let options = {
            to: data.to,
            subject: 'New message from a brand',
            message
        }
        return emailer.sendEmail(options);
    },

    addNewUser(data) {
        let message = `<p>${data.name} invited you to AB2CD admin panel.<br/> Email: ${data.email} <br/> Password: ${data.password} <a href="${config.app.basePath}">Login here</a> </p>`
        let options = {
            to: data.email,
            subject: 'Invitation from AB2CD',
            message
        }
        return emailer.sendEmail(options);
    }
};