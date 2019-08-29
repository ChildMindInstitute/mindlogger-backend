# -*- coding: utf-8 -*-
import click
import os
import paramiko
import sys

from girderformindlogger import logprint
from girderformindlogger.api.sftp import SftpServer

DEFAULT_PORT = 8022


@click.command(name='sftpd', short_help='Run the Girder SFTP service.',
               help='Run the Girder SFTP service.')
@click.option('-i', '--identity-file', show_default=True,
              default=os.path.expanduser(os.path.join('~', '.ssh', 'id_rsa')),
              help='The identity (private key) file to use')
@click.option('-H', '--host', show_default=True, default='localhost',
              help='The interface to bind to')
@click.option('-p', '--port', show_default=True, default=DEFAULT_PORT, type=int,
              help='The port to bind to')
def main(identity_file, port, host):
    """
    This is the entrypoint of the girderformindlogger sftpd program. It should not be
    called from python code.
    """
    try:
        hostKey = paramiko.RSAKey.from_private_key_file(identity_file)
    except paramiko.ssh_exception.PasswordRequiredException:
        logprint.error(
            'Error: encrypted key files are not supported (%s).' % identity_file, file=sys.stderr)
        sys.exit(1)

    server = SftpServer((host, port), hostKey)
    logprint.info('Girder SFTP service listening on %s:%d.' % (host, port))

    try:
        server.serve_forever()
    except (SystemExit, KeyboardInterrupt):
        server.server_close()
