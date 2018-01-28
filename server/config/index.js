export default {
    mail: {
        from_name: 'Child Mind Institute',
        from_email: 'noreply@childmindinstitute.com',
        is_smtp: true,
        smtp: {
            host: 'email-smtp.us-east-1.amazonaws.com',
            port: '465',
            user: process.env.MAIL_USER,
            password: process.env.MAIL_PASSWORD,
            isSecure: true
        }
    },
}