require('dotenv').config();
export default {
    mail: {
        from_name: 'Child Mind Institute',
        from_email: 'mindlogger@childmind.org',
        is_smtp: true,
        smtp: {
            host: 'email-smtp.us-east-1.amazonaws.com',
            port: '465',
            user: process.env.MAIL_USER,
            password: process.env.MAIL_PASSWORD,
            isSecure: true
        }
    },
    app: {
        basePath: 'http://mindlogger.childmind.org'
    },
    s3: {
        bucket: "mindloggerimages",
        region: "us-east-1",
        accessKeyId: process.env.AWS_KEY_ID,
        secretAccesskey: process.env.AWS_SECRET_KEY,
    }
}