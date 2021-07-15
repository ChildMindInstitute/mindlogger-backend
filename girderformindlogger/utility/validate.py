import re
import json
from functools import wraps
from cerberus import Validator
from girderformindlogger.exceptions import ValidationException
import mimetypes

def email_validator(field, value, error):
    if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', value):
        error(field, "Incorrect email format")


def symbol_validator(field, value, error):
    if re.match(r'(?=.*[!@#$%^&*<>{}])', value):
        error(field, "Field contains incorrect symbols")


def validator(schema):
    def _wrapper(f):
        @wraps(f)
        def validate(*args, **kwargs):
            v = Validator(schema)
            params = kwargs
            if len(args):
                params = dict(zip(schema.keys(), args))
            if v.validate(params):
                f(*args, **kwargs)
            else:
                raise ValidationException(json.dumps(v.errors))
        return validate
    return _wrapper


def isUrlValid(value):
    
    code = 'invalid'
    message = ('Enter a valid URL.')
    schemes = ['http', 'https', 'ftp', 'ftps']
    unsafe_chars = frozenset('\t\r\n')
    
    if not isinstance(value, str):
        return False
    
    if unsafe_chars.intersection(value):
        return False
    
    # Check if the scheme is valid.
    scheme = value.split('://')[0].lower()
    if scheme not in schemes:
        return False
    
    ul = '\u00a1-\uffff'  # Unicode letters range (must not be a raw string).

    # IP patterns
    ipv4_re = r'(?:0|25[0-5]|2[0-4]\d|1\d?\d?|[1-9]\d?)(?:\.(?:0|25[0-5]|2[0-4]\d|1\d?\d?|[1-9]\d?)){3}'
    ipv6_re = r'\[[0-9a-f:.]+\]'  # (simple regex, validated later)

    # Host patterns
    hostname_re = r'[a-z' + ul + r'0-9](?:[a-z' + ul + r'0-9-]{0,61}[a-z' + ul + r'0-9])?'
    # Max length for domain name labels is 63 characters per RFC 1034 sec. 3.1
    domain_re = r'(?:\.(?!-)[a-z' + ul + r'0-9-]{1,63}(?<!-))*'
    tld_re = (
        r'\.'                                # dot
        r'(?!-)'                             # can't start with a dash
        r'(?:[a-z' + ul + '-]{2,63}'         # domain label
        r'|xn--[a-z0-9]{1,59})'              # or punycode label
        r'(?<!-)'                            # can't end with a dash
        r'\.?'                               # may have a trailing dot
    )
    host_re = '(' + hostname_re + domain_re + tld_re + '|localhost)'

    regex = re.compile(
        r'^(?:[a-z0-9.+-]*)://'  # scheme is validated separately
        r'(?:[^\s:@/]+(?::[^\s:@/]*)?@)?'  # user:pass authentication
        r'(?:' + ipv4_re + '|' + ipv6_re + '|' + host_re + ')'
        r'(?::\d{2,5})?'  # port
        r'(?:[/?#][^\s]*)?'  # resource path
        r'\Z', re.IGNORECASE)
    
    return re.match(regex, value) is not None


def pathIsImage(url):    
    mimetype, encoding = mimetypes.guess_type(url)
    if mimetype == None:
        return False
    return mimetype.startswith('image')


def isValidImageUrl(url):
    
    result = pathIsImage(url)
    
    if result:
        result = isUrlValid(url)
        
    return result