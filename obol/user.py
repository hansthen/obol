#!/usr/bin/env python
from retrying import retry
from ldif import LDIFWriter
import sys
import ldap
import os
import hashlib
import logging

from cliff.command import Command

logger = logging.getLogger(__name__)


def make_secret(password):
    """Encodes the given password as a base64 SSHA hash+salt buffer"""
    if password.startswith('{SSHA}'):
        return password

    salt = os.urandom(4)

    # hash the password and append the salt
    sha = hashlib.sha1(password)
    sha.update(salt)

    # create a base64 encoded string of the concatenated digest + salt
    digest_salt = '{}{}'.format(sha.digest(), salt).encode('base64').strip()

    # now tag the digest above with the {SSHA} tag
    tagged_digest_salt = '{{SSHA}}{}'.format(digest_salt)

    return tagged_digest_salt


class Init(Command):
    """Initialize the tree"""

    def get_parser(self, name):
        parser = super(Init, self).get_parser(name)
        parser.add_argument('--user_tree',
                            default=self.app.default('user_tree', 'ou=People'))
        parser.add_argument('--group_tree',
                            default=self.app.default('group_tree', 'ou=Group'))

        return parser

    def take_action(self, args):
        b = self.app_args.b
        conn = self.app.conn

        group_tree = args.group_tree
        user_tree = args.user_tree

        dn = '%s' % (b)
        add_record = [
            ('objectclass', ['domain']),
        ]
        conn.add_s(dn, add_record)

        dn = '%s,%s' % (user_tree, b)
        add_record = [
            ('objectclass', ['top', 'organizationalUnit']),
            ('ou', [user_tree])
        ]
        conn.add_s(dn, add_record)

        dn = '%s,%s' % (group_tree, b)
        add_record = [
            ('objectclass', ['top', 'organizationalUnit']),
            ('ou', [group_tree])
        ]
        conn.add_s(dn, add_record)

        dn = 'cn=uid,%s' % b
        add_record = [
            ('objectclass', ['uidNext']),
            ('uidNumber', ['1050'])
        ]
        conn.add_s(dn, add_record)

        dn = 'cn=gid,%s' % b
        add_record = [
            ('objectclass', ['uidNext']),
            ('uidNumber', ['150'])
        ]
        conn.add_s(dn, add_record)


class UserAdd(Command):
    """Add a user to the LDAP"""

    @retry(stop_max_delay=10000)
    def increment_uid(self, b):
        """Generate a new userid"""
        conn = self.app.conn
        dn = 'cn=uid,%s' % b
        filter = 'objectclass=*'
        attrs = ['uidNumber']

        try:
            result = conn.search_s(dn, ldap.SCOPE_SUBTREE, filter, attrs)
            uidNumber = result[0][1]['uidNumber'][0]

            mod_attrs = [(ldap.MOD_DELETE, 'uidNumber', uidNumber),
                         (ldap.MOD_ADD, 'uidNumber', str(int(uidNumber)+1))]

            conn.modify_s(dn, mod_attrs)
        except Exception:
            raise
        return uidNumber

    def get_parser(self, name):
        parser = super(UserAdd, self).get_parser(name)
        parser.add_argument('username')
        parser.add_argument('--subtree',
                            default=self.app.default('user_tree', 'ou=People'))
        parser.add_argument('--grouptree',
                            default=self.app.default('group_tree', 'ou=Group'))
        parser.add_argument('--uidNumber')
        parser.add_argument('--password')
        parser.add_argument('--cn', metavar="COMMON NAME")
        parser.add_argument('--sn', metavar="SURNAME")
        parser.add_argument('--givenName')
        parser.add_argument('--shell', default='/bin/bash')
        parser.add_argument('--groups', type=csep,
                            help="a comma separated list of groups")

        return parser

    def take_action(self, args):
        b = self.app.options.b
        username = args.username
        uidNumber = args.uidNumber
        cn = args.cn
        sn = args.sn
        givenName = args.givenName
        password = args.password
        context = args.subtree
        shell = args.shell
        groups = args.groups
        grouptree = args.grouptree
        conn = self.app.conn

        if not uidNumber:
            uidNumber = self.increment_uid(b)

        # first add the group
        dn = 'cn=%s,%s,%s' % (username, context, b)
        logger.debug(dn)
        add_record = [
            ('objectclass', ['top', 'posixGroup']),
            ('cn', [username]),
            ('memberuid', [uidNumber]),
            ('gidNumber', [uidNumber])
        ]
        conn.add_s(dn, add_record)

        # now add the user
        dn = 'uid=%s,%s,%s' % (username, context, b)
        logger.debug(dn)

        # set some default values
        if not cn:
            cn = username
        if not sn:
            sn = username

        add_record = [
            ('objectclass', ['top', 'person', 'organizationalPerson',
                             'inetOrgPerson', 'posixAccount',
                             'shadowAccount']),
            ('uid', [username]),
            ('cn', [cn]),
            ('sn', [sn]),
            ('loginShell', [shell]),
            ('uidNumber', [uidNumber]),
            ('gidNumber', [uidNumber]),
            ('homeDirectory', ['/home/%s' % username])
        ]

        if givenName:
            add_record.append(('givenName', [givenName]))
        if password:
            password = make_secret(password)
            add_record.append(('userPassword', [password]))

        conn.add_s(dn, add_record)

        if groups:
            for group in groups:
                dn = 'cn=%s,%s,%s' % (group, grouptree, b)
                try:
                    mod_attrs = []
                    mod_attrs.append((ldap.MOD_ADD, 'memberuid', username))
                    conn.modify_s(dn, mod_attrs)
                except Exception as error:
                    print("Error adding %s to %s: %s" %
                          (username, group, error))


class UserDelete(Command):
    """Delete a user from the LDAP"""

    def get_parser(self, name):
        parser = super(UserDelete, self).get_parser(name)
        parser.add_argument('username')
        parser.add_argument('--subtree',
                            default=self.app.default('user_tree', 'ou=People'))
        return parser

    def take_action(self, args):
        b = self.app.options.b
        conn = self.app.conn
        username = args.username
        context = args.subtree

        # First delete the user
        try:
            dn = 'uid=%s,%s,%s' % (username, context, b)
            conn.delete_s(dn)
        except Exception as e:
            print(e)

        base_dn = '%s,%s' % (context, b)
        filter = '(memberuid=%s)' % username
        attrs = ['']
        groups = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, filter, attrs)
        dns = [_dn for _dn, _attrs in groups]

        try:
            for dn in dns:
                mod_attrs = [(ldap.MOD_DELETE, 'memberuid', username)]
                conn.modify_s(dn, mod_attrs)
        except Exception as e:
            print(e)

        # Next delete the group
        try:
            dn = 'cn=%s,%s,%s' % (username, context, b)
            conn.delete_s(dn)
        except Exception as e:
            print(e)


class UserList(Command):
    """List all users"""
    log = logging.getLogger(__name__)

    def get_parser(self, name):
        parser = super(UserList, self).get_parser(name)
        parser.add_argument('--subtree',
                            default=self.app.default('user_tree', 'ou=People'))
        return parser

    def take_action(self, args):
        """List users defined in the system"""
        b = self.app.options.b
        conn = self.app.conn
        context = args.subtree

        base_dn = '%s,%s' % (context, b)
        filter = '(objectclass=person)'
        attrs = ['uid']
        for _, attrs in conn.search_s(base_dn,
                                      ldap.SCOPE_SUBTREE, filter, attrs):
            print(attrs['uid'][0])


class UserModify(Command):
    """Modify a user"""
    def get_parser(self, name):
        parser = super(UserModify, self).get_parser(name)
        parser.add_argument('username')
        parser.add_argument('--subtree',
                            default=self.app.default('user_tree', 'ou=People'))
        parser.add_argument('--cn')
        parser.add_argument('--sn')
        parser.add_argument('--givenName')
        parser.add_argument('--shell')
        return parser

    def take_action(self, args):
        username = args.username
        context = args.subtree
        b = self.app.options.b
        conn = self.app.conn

        dn = 'uid=%s,%s,%s' % (username, context, b)

        mod_attrs = []
        for key in ['cn', 'sn', 'givenName', 'shell']:
            value = getattr(args, key)
            if not value:
                continue
            if key == 'shell':
                key = 'loginShell'
            mod_attrs.append((ldap.MOD_DELETE, key, None))
            mod_attrs.append((ldap.MOD_ADD, key, value))
        conn.modify_s(dn, mod_attrs)


class UserReset(Command):
    """Reset a user's password"""
    def get_parser(self, name):
        parser = super(UserReset, self).get_parser(name)
        parser.add_argument('username')
        parser.add_argument('--subtree',
                            default=self.app.default('user_tree', 'ou=People'))
        parser.add_argument('--password')
        return parser

    def take_action(self, args):
        username = args.username
        password = args.password
        context = args.subtree
        b = self.app.options.b
        conn = self.app.conn

        dn = 'uid=%s,%s,%s' % (username, context, b)
        conn.passwd_s(dn, None, password)


class UserShow(Command):
    """Show a user"""
    def get_parser(self, name):
        parser = super(UserShow, self).get_parser(name)
        parser.add_argument('username')
        parser.add_argument('--subtree',
                            default=self.app.default('user_tree', 'ou=People'))
        return parser

    def take_action(self, args):
        username = args.username
        context = args.subtree
        b = self.app.options.b
        conn = self.app.conn

        base_dn = '%s,%s' % (context, b)
        filter = '(uid=%s)' % username
        writer = LDIFWriter(sys.stdout)
        for dn, attrs in conn.search_s(base_dn, ldap.SCOPE_SUBTREE, filter):
            writer.unparse(dn, attrs)


def csep(s):
    "A utility function to split a comma separated string into a list"
    try:
        return s.split(',')
    except:
        raise ValueError("Illegal groups value")
