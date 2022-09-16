# -*- coding: utf-8 -*-
import os
import re
import six
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from mako.lookup import TemplateLookup
from girderformindlogger import events
from girderformindlogger import logger
from girderformindlogger.constants import PACKAGE_DIR
from girderformindlogger.settings import SettingKey
from girderformindlogger.exceptions import AccessException


def htmlUserList(userlist, showEmail=False):
    htmlList = "</li><li>".join([
        formatUserString(userlist[u]) for u in userlist
    ])
    return("<ul><li>{}</li></ul>".format(htmlList) if len(htmlList) else "")

def formatUserString(u):
    """
    :param u: user display profile
    :type u: dict
    :returns: str
    """
    if not isinstance(u, dict):
        return("")
    return(
        "{name} {email}".format(
            name=u.get("displayName", ""),
            email="({})".format(u["email"]) if "email" in u and u["email"] != "" and not u.get('email_encrypted', None) else ""
        ).strip()
    )

def validateEmailAddress(address):
    """
    Determines whether a string is a valid email address.

    This implements the grammar from 4.10.5.1.5 of the HTML Standard.

    :param address: The string to test.
    :type address: str
    :rtype: bool
    """
    # https://html.spec.whatwg.org/multipage/input.html#valid-e-mail-address
    return re.match(
        r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+'
        r'@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$',
        address
    ) is not None


def getEmailUrlPrefix():
    """
    Return the URL prefix for links back to the server. This is the link to the
    server root, so Girder-level path information and any query parameters or
    fragment value should be appended to this value.
    """
    from girderformindlogger.models.setting import Setting
    return Setting().get(SettingKey.EMAIL_HOST)


_templateDir = os.path.join(PACKAGE_DIR, 'mail_templates')
_templateLookup = TemplateLookup(directories=[_templateDir], collection_size=50)


def addTemplateDirectory(dir, prepend=False):
    """
    Adds a directory to the search path for mail templates. This is useful
    for plugins that have their own set of mail templates.

    :param dir: The directory to add to the template lookup path.
    :type dir: str
    :param prepend: If True, adds this directory at the beginning of the path so
        that it will override any existing templates with the same name.
        Otherwise appends to the end of the lookup path.
    :type prepend: bool
    """
    idx = 0 if prepend else len(_templateLookup.directories)
    _templateLookup.directories.insert(idx, dir)


def renderTemplate(name, params=None):
    """
    Renders one of the HTML mail templates located in girderformindlogger/mail_templates.

    :param name: The name of the file inside girderformindlogger/mail_templates to render.
    :param params: The parameters to pass when rendering the template.
    :type params: dict
    :returns: The rendered template as a string of HTML.
    """
    from girderformindlogger.models.setting import Setting

    if not params:
        params = {}

    if 'host' not in params:
        params['host'] = getEmailUrlPrefix()
    if 'brandName' not in params:
        params['brandName'] = Setting().get(SettingKey.BRAND_NAME)

    template = _templateLookup.get_template(name)
    return template.render(**params)


def _createMessage(subject, text, to, bcc, attachments = []):
    from girderformindlogger.models.setting import Setting

    # Coerce and validate arguments
    if isinstance(to, six.string_types):
        to = [to]
    if isinstance(bcc, six.string_types):
        bcc = [bcc]
    elif bcc is None:
        bcc = []
    if not to and not bcc:
        raise Exception('You must specify email recipients via "to" or "bcc".')

    if not subject:
        subject = '[no subject]'

    if isinstance(text, six.text_type):
        text = text.encode('utf8')

    # Build message
    msg = MIMEMultipart()
    if to:
        msg['To'] = ', '.join(to)
    if bcc:
        msg['Bcc'] = ', '.join(bcc)
    msg['Subject'] = subject
    msg['From'] = Setting().get(SettingKey.EMAIL_FROM_ADDRESS)
    msg.attach(MIMEText(text, 'html', 'UTF-8'))

    for attachment in attachments:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment['file'].read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {attachment['name']}",
        )
        msg.attach(part)

    # Compute recipients
    recipients = list(set(to) | set(bcc))

    return msg, recipients


class _SMTPConnection(object):
    def __init__(self, host, port=None, encryption=None,
                 username=None, password=None):
        self.host = host
        self.port = port
        self.encryption = encryption
        self.username = username
        self.password = password

    def __enter__(self):
        try:
            if self.encryption == 'ssl':
                self.connection = smtplib.SMTP_SSL(self.host, self.port)
            else:
                self.connection = smtplib.SMTP(self.host, self.port)
                if self.encryption == 'starttls':
                    self.connection.starttls()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
        except:
            raise AccessException(
                "An error occured when we were sending message. "
                "Please try again later."
            )
        return self

    def send(self, fromAddress, toAddresses, message):
        self.connection.sendmail(fromAddress, toAddresses, message)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (exc_tb):
            raise AccessException(
                "An error occured when we were sending message. "
                "Please try again later."
            )
        self.connection.quit()


def _submitEmail(msg, recipients):
    from girderformindlogger.models.setting import Setting

    setting = Setting()
    smtp = _SMTPConnection(
        host=setting.get(SettingKey.SMTP_HOST),
        port=setting.get(SettingKey.SMTP_PORT),
        encryption=setting.get(SettingKey.SMTP_ENCRYPTION),
        username=setting.get(SettingKey.SMTP_USERNAME),
        password=setting.get(SettingKey.SMTP_PASSWORD)
    )

    logger.info('Sending email to %s through %s', ', '.join(recipients), smtp.host)

    with smtp:
        smtp.send(msg['From'], recipients, msg.as_string())


def _sendmail(event):
    msg = event.info['message']
    recipients = event.info['recipients']
    _submitEmail(msg, recipients)


events.bind('_sendmail', 'core.email', _sendmail)


def sendMailSync(subject, text, to, bcc=None, attachments=[]):
    """Send an email synchronously."""
    msg, recipients = _createMessage(subject, text, to, bcc, attachments)

    _submitEmail(msg, recipients)


def sendMail(subject, text, to, bcc=None, attachments=[]):
    """
    Send an email asynchronously.

    :param subject: The subject line of the email.
    :type subject: str
    :param text: The body of the email.
    :type text: str
    :param to: The list of recipient email addresses.
    :type to: list
    :param bcc: Recipient email addresses that should be specified using the Bcc header.
    :type bcc: list or None
    """
    msg, recipients = _createMessage(subject, text, to, bcc, attachments)

    events.daemon.trigger('_sendmail', info={
        'message': msg,
        'recipients': recipients
    })


def sendMailToAdmins(subject, text):
    """Send an email asynchronously to site admins."""
    from girderformindlogger.models.user import User

    to = [u['email'] for u in User().getAdmins()]
    sendMail(subject, text, to)


def sendMailIndividually(subject, text, to):
    """Send emails asynchronously to all recipients individually."""
    for address in to:
        sendMail(address, subject, text)
