# -*- coding: utf-8 -*-
#
# Example of usage:
# export PYTHONUNBUFFERED=1
# girderformindlogger re_encrypt --random
# girderformindlogger re_encrypt --key "XXXXXX" --new "YYYYYY" --debug
# girderformindlogger re_encrypt --key "XXXXXX" --new "YYYYYY" --model=User --force
#

import click
import pymongo
import random, string

from girderformindlogger.models.invitation import Invitation
from girderformindlogger.models.note import Note
from girderformindlogger.models.profile import Profile
from girderformindlogger.models.response_alerts import ResponseAlerts
from girderformindlogger.models.response_folder import ResponseItem
from girderformindlogger.models.response_tokens import ResponseTokens
from girderformindlogger.models.user import User


@click.command(name='re_encrypt', short_help='Re-encrypt.', help='Re-encrypt.')
@click.option('--debug', default=False, is_flag=True, help='Print keys.')
@click.option('--random', default=False, is_flag=True, help='Print random AES key.')
@click.option('--model', default=None, type=click.Choice(['User', 'Note', 'Invitation', 'Profile', 'ResponseAlerts', 'ResponseItem', 'ResponseTokens']),
              help='Specify the model to re-encrypt')
@click.option('--force', default=False, is_flag=True, help='')
@click.option('-k', '--key', help='The current AES key. If not specified the default will be used.')
@click.option('-n', '--new', help='The new AES key')
def main(debug, random, model, force, key, new):
    if debug:
        if key:
            print('key: %s' % (key))
        if new:
            print('new: %s' % (new))
        exit(0)

    if random and force:
        raise click.ClickException('Conflict between --random and --force')

    if random:
        print(random_password())
        exit(0)

    if force:
        if not model:
            raise click.ClickException('--model must be defined')
        if not new:
            raise click.ClickException('--new must be defined')
        if not key:
            key = User().AES_KEY

        if model == 'User':
            re_encrypt(model, User(), key, new)
        elif model == 'Note':
            re_encrypt(model, Note(), key, new)
        elif model == 'ResponseTokens':
            re_encrypt(model, ResponseTokens(), key, new)
        elif model == 'Invitation':
            re_encrypt(model, Invitation(), key, new)
        elif model == 'Profile':
            re_encrypt(model, Profile(), key, new)
        elif model == 'ResponseAlerts':
            re_encrypt(model, ResponseAlerts(), key, new)
        elif model == 'ResponseItem':
            re_encrypt(model, ResponseItem(), key, new)

        exit(0)


def re_encrypt(model, model_obj, key, new):
    ids = list(model_obj.collection.find({}, {"_id": 1}).sort([("created", pymongo.ASCENDING)]))
    print(model, 'records total', len(ids))
    for idx, id in enumerate(ids, start=1):
        model_obj.baseKey = model_obj.AES_KEY = bytes(key, 'utf8')
        obj = model_obj.findOne(id)
        model_obj.baseKey = model_obj.AES_KEY = bytes(new, 'utf8')
        model_obj.save(obj)
        if idx % 1000 == 0: print(idx)
        elif idx % 100 == 0: print('.', end='')
    print('\nEnd')

def random_password(length=32):
    chars = string.ascii_letters + string.digits + '!@#$%^&*()/+'
    rnd = random.SystemRandom()
    return ''.join(rnd.choice(chars) for i in range(length))
