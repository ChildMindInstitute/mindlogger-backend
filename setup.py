# -*- coding: utf-8 -*-
import os

from setuptools import setup, find_packages


def prerelease_local_scheme(version):
    """Return local scheme version unless building on master in CircleCI.
    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """
    from setuptools_scm.version import get_local_node_and_date

    if os.getenv('CIRCLE_BRANCH') == 'master':
        return ''
    else:
        return get_local_node_and_date(version)


with open('README.rst') as f:
    readme = f.read()

installReqs = [
	'setuptools==50.3.2',
    'boto3',
    'botocore',
    'cherrypy_cors==1.6',
    # CherryPy version is restricted due to a bug in versions >=11.1
    # https://github.com/cherrypy/cherrypy/issues/1662
    'CherryPy<11.1',
    'rq==1.5.0',
	'rq-scheduler==0.10.0',
	'pyfcm==1.4.7',
    'pycryptodomex',
    'json5',
    'click',
    'click-plugins',
    'cryptography==3.3.2',
    'cerberus==1.3.2',
    'backports-datetime-fromisoformat==1.0.0',
	'backports.functools-lru-cache==1.5',
    'dictdiffer',
    'dnspython',
    'dogpile.cache',
    'filelock',
    "funcsigs ; python_version < '3'",
    'isodate',
    'json5==0.9.5',
    'jsonschema',
    'Mako',
    'pandas==0.25.1',
    'passlib [bcrypt,totp]',
    'pymongo>=3.6',
    'PyYAML',
    'psutil==5.6.6',
    'pyld>=2.0.2',
    'pyOpenSSL',
    'python-dateutil==2.6.1',
    'pytz',
    'qrcode[pil]',
    'redis==3.5.2',
    'requests',
    "shutilwhich ; python_version < '3'",
    'sentry-sdk==0.16.0',
    'simplejson',
    'six>=1.9',
    'tzlocal>=1.5.1'
]

extrasReqs = {
    'sftp': [
        'paramiko'
    ],
    'mount': [
        'fusepy>=3.0'
    ]
}

setup(
    name='girderformindlogger',
    use_scm_version={'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools-scm'],
    description='Web-based data management platform customized for MindLogger',
    long_description=readme,
    author='Child Mind Institute MATTER Lab & Kitware',
    author_email='matterlab@childmind.org',
    url='https://github.com/ChildMindInstitute/mindlogger-app-backend',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6'
    ],
    packages=find_packages(
        exclude=('girderformindlogger.test', 'tests.*', 'tests', '*.plugin_tests.*', '*.plugin_tests')
    ),
    include_package_data=True,
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    install_requires=installReqs,
    extras_require=extrasReqs,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'girder-server = girderformindlogger.cli.serve:main',
            'girder-sftpd = girderformindlogger.cli.sftpd:main',
            'girder-shell = girderformindlogger.cli.shell:main',
            'girderformindlogger = girderformindlogger.cli:main'
        ],
        'girderformindlogger.cli_plugins': [
            'serve = girderformindlogger.cli.serve:main',
            'mount = girderformindlogger.cli.mount:main',
            'shell = girderformindlogger.cli.shell:main',
            'sftpd = girderformindlogger.cli.sftpd:main',
            'build = girderformindlogger.cli.build:main'
        ]
    }
)
