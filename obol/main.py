#!/usr/bin/python
import sys
import logging

from cliff.app import App
from cliff.commandmanager import CommandManager

import ldap
import os
from ConfigParser import ConfigParser

from . import user, group


class ObolApp(App):
    def __init__(self):
        manager = CommandManager('obol.app')
        manager.add_command('init', user.Init)
        manager.add_command('user list', user.UserList)
        manager.add_command('user add', user.UserAdd)
        manager.add_command('user delete', user.UserDelete)
        manager.add_command('user modify', user.UserModify)
        manager.add_command('user reset', user.UserReset)
        manager.add_command('user show', user.UserShow)
        manager.add_command('group show', group.GroupShow)
        manager.add_command('group list', group.GroupList)
        manager.add_command('group add', group.GroupAdd)
        manager.add_command('group delete', group.GroupDelete)
        manager.add_command('group useradd', group.GroupAddUsers)
        manager.add_command('group userdel', group.GroupDelUsers)
        manager.add_command('group addusers', group.GroupAddUsers)
        manager.add_command('group delusers', group.GroupDelUsers)

        super(ObolApp, self).__init__(
            description='Obol: LDAP command line tool',
            version='2.0',
            command_manager=manager,
            deferred_help=True,
            )

        config = ConfigParser({'user_tree': 'ou=People',
                               'group_tree': 'ou=Group'})
        config.read(['/etc/obol/obol.config',
                     os.path.expanduser('~/.obol.cfg')])
        self.config = config

    def default(self, key, default=''):
        """A utility function to retrieve defaults from a config file"""
        try:
            return self.config.get('default', key)
        except:
            return default

    def initialize_app(self, argv):
        self.LOG.debug('initialize_app')
        dn = self.options.D
        password = self.options.w
        host = self.options.H
        conn = ldap.initialize(host)
        conn.simple_bind_s(dn, password)
        self.conn = conn

    def build_option_parser(self, description, version, argparse_kwargs=None):
        parser = super(ObolApp, self).build_option_parser(
            description,
            version,
            argparse_kwargs
            )

        parser.add_argument('-D', metavar='BIND DN',
                            default=self.default('bindDN',
                                                 'cn=Manager,dc=local'))
        parser.add_argument('-w', metavar='BIND PASSWORD',
                            default=self.default('password'))
        parser.add_argument('-H', metavar='HOST',
                            default=self.default('host', 'ldap://localhost'))
        parser.add_argument('-b', metavar='BASE_DN',
                            default=self.default('baseDN', 'dc=local'))
        loglevels = [key for key in logging._levelNames
                     if isinstance(key, str)]

        parser.add_argument('--logLevel', choices=loglevels,
                            default=self.default('logLevel', 'INFO'))
        return parser

    def prepare_to_run_command(self, cmd):
        self.LOG.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.LOG.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.LOG.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    myapp = ObolApp()
    return myapp.run(argv)


if __name__ == "__main__" and __package__ is None:
    __package__ = "obol"

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
