# -*- coding: utf-8 -*-
import json
import os
from pkg_resources import resource_filename
from subprocess import check_call
import shutil
import sys

import click
import six

import girderformindlogger
from girderformindlogger.constants import STATIC_ROOT_DIR, ServerMode
from girderformindlogger.plugin import allPlugins, getPlugin
from girderformindlogger.utility import server

# monkey patch shutil for python < 3
if not six.PY3:
    import shutilwhich  # noqa

_GIRDER_BUILD_ASSETS_PATH = os.path.realpath(resource_filename('girderformindlogger', 'web_client'))


@click.command(name='build', help='Build web client static assets.')
@click.option('--dev', default=False, is_flag=True, help='Alias for --mode=development')
@click.option('--mode', type=click.Choice([ServerMode.PRODUCTION, ServerMode.DEVELOPMENT]),
              default=None, show_default=True, help='Specify the server mode')
@click.option('--watch', default=False, is_flag=True,
              help='Build girderformindlogger library bundle in '
              'watch mode (implies --mode=development --no-reinstall).')
@click.option('--watch-plugin',
              help='Build a girderformindlogger plugin bundle in '
              'watch mode (implies --mode=development --no-reinstall).')
@click.option('--npm', default=os.getenv('NPM_EXE', 'npm'),
              help='Full path to the npm executable to use.')
@click.option('--reinstall/--no-reinstall', default=True,
              help='Force regenerate node_modules.')
def main(dev, mode, watch, watch_plugin, npm, reinstall):
    if shutil.which(npm) is None:
        raise click.UsageError(
            'No npm executable was detected.  Please ensure the npm executable is in your '
            'path, use the --npm flag, or set the "NPM_EXE" environment variable.'
        )

    if dev and mode:
        raise click.ClickException('Conflict between --dev and --mode')
    if dev:
        mode = ServerMode.DEVELOPMENT

    if watch and watch_plugin:
        raise click.UsageError('--watch and --watch-plugins cannot be used together')
    if watch or watch_plugin:
        mode = ServerMode.DEVELOPMENT
        reinstall = False

    staging = _GIRDER_BUILD_ASSETS_PATH
    _generatePackageJSON(staging, os.path.join(_GIRDER_BUILD_ASSETS_PATH, 'package.json.template'))

    if not os.path.isdir(os.path.join(staging, 'node_modules')) or reinstall:
        # The autogeneration of package.json breaks how package-lock.json is
        # intended to work.  If we don't delete it first, you will frequently
        # get "file doesn't exist" errors.
        npmLockFile = os.path.join(staging, 'package-lock.json')
        if os.path.exists(npmLockFile):
            os.unlink(npmLockFile)
        installCommand = [npm, 'install']
        if mode == ServerMode.PRODUCTION:
            installCommand.append('--production')
        try:
            check_call(installCommand, cwd=staging)
        except FileNotFoundError:
            check_call(installCommand, cwd=staging, shell=True)   

    quiet = '--no-progress=false' if sys.stdout.isatty() else '--no-progress=true'
    buildCommand = [
        npm, 'run', 'build', '--',
        '--girder-version=%s' % girderformindlogger.__version__,
        '--static-path=%s' % STATIC_ROOT_DIR,
        '--static-public-path=%s' % server.getStaticPublicPath(),
        quiet
    ]
    if watch:
        buildCommand.append('--watch')
    if watch_plugin:
        buildCommand.extend([
            '--watch',
            'webpack:plugin_%s' % watch_plugin
        ])
    if mode == ServerMode.DEVELOPMENT:
        buildCommand.append('--env=dev')
    else:
        buildCommand.append('--env=prod')
    try:
        check_call(buildCommand, cwd=staging)
    except FileNotFoundError:
        check_call(buildCommand, cwd=staging, shell=True)


def _collectPluginDependencies():
    packages = {}
    for pluginName in allPlugins():
        plugin = getPlugin(pluginName)
        packages.update(plugin.npmPackages())
    return packages


def _generatePackageJSON(staging, source):
    with open(source, 'r') as f:
        sourceJSON = json.load(f)
    deps = sourceJSON['dependencies']
    deps['@girder/core'] = 'file:%s' % os.path.join(
        os.path.dirname(source),
        'src'
    )
    plugins = _collectPluginDependencies()
    deps.update(plugins)
    sourceJSON['girderformindlogger'] = {
        'plugins': list(plugins.keys())
    }
    with open(os.path.join(staging, 'package.json'), 'w') as f:
        json.dump(sourceJSON, f)
