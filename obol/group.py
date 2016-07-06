#!/usr/bin/env python
from retrying import retry
from ldif import LDIFWriter
import sys
import ldap

from cliff.command import Command


class GroupList(Command):
    """List Users"""
    def get_parser(self, name):
        parser = super(GroupList, self).get_parser(name)
        parser.add_argument('--subtree',
                            default=self.app.default('group_tree', 'ou=Group'))
        return parser

    def take_action(self, args):
        conn = self.app.conn
        b = self.app.options.b
        context = args.subtree

        base_dn = '%s,%s' % (context, b)
        filter = '(objectclass=posixGroup)'
        for _, attrs in conn.search_s(base_dn, ldap.SCOPE_SUBTREE, filter):
            print(attrs['cn'][0])


class GroupDelete(Command):
    """Delete a user from the system"""
    def get_parser(self, name):
        parser = super(GroupDelete, self).get_parser(name)

        parser.add_argument('groupname')
        parser.add_argument('--subtree',
                            default=self.app.default('group_tree', 'ou=Group'))

        return parser

    def take_action(self, args):
        conn = self.app.conn
        b = self.app.options.b
        context = args.subtree
        groupname = args.groupname

        try:
            dn = 'cn=%s,%s,%s' % (groupname, context, b)
            conn.delete_s(dn)
        except Exception as e:
            print(e)


class GroupAdd(Command):
    """Add a group to the LDAP"""
    def get_parser(self, name):
        parser = super(GroupAdd, self).get_parser(name)
        parser.add_argument('groupname')
        parser.add_argument('--subtree',
                            default=self.app.default('group_tree', 'ou=Group'))
        parser.add_argument('--gidNumber')
        return parser

    def take_action(self, args):
        conn = self.app.conn
        b = self.app.options.b
        context = args.subtree
        gidNumber = args.gidNumber
        groupname = args.groupname

        if not gidNumber:
            gidNumber = self.increment_gid(b)

        # first add the group
        dn = 'cn=%s,%s,%s' % (groupname, context, b)
        add_record = [
            ('objectclass', ['top', 'posixGroup']),
            ('cn', [groupname]),
            ('gidNumber', [gidNumber])
        ]
        conn.add_s(dn, add_record)

    @retry(stop_max_delay=10000)
    def increment_gid(self, b):
        """Generate a new groupid"""
        conn = self.app.conn
        dn = 'cn=gid,%s' % b
        filter = 'objectclass=*'
        attrs = ['uidNumber']

        try:
            result = conn.search_s(dn, ldap.SCOPE_SUBTREE, filter, attrs)
            gidNumber = result[0][1]['uidNumber'][0]

            mod_attrs = [(ldap.MOD_DELETE, 'uidNumber', gidNumber),
                         (ldap.MOD_ADD, 'uidNumber', str(int(gidNumber)+1))]

            conn.modify_s(dn, mod_attrs)
        except Exception as e:
            print(e)
        return gidNumber


class GroupAddUsers(Command):
    """Add a group to the LDAP"""
    def get_parser(self, name):
        parser = super(GroupAddUsers, self).get_parser(name)
        parser.add_argument('groupname')
        parser.add_argument('--subtree',
                            default=self.app.default('group_tree', 'ou=Group'))
        parser.add_argument('username', nargs='+')

        return parser

    def take_action(self, args):
        """Add users to a group"""
        conn = self.app.conn
        b = self.app.options.b
        groupname = args.groupname
        username = args.username
        context = args.subtree

        dn = 'cn=%s,%s,%s' % (groupname, context, b)
        for name in username:
            try:
                mod_attrs = []
                mod_attrs.append((ldap.MOD_ADD, 'memberuid', name))
                conn.modify_s(dn, mod_attrs)
            except Exception as error:
                print("Error adding %s to %s: %s" % (name, groupname, error))


class GroupDelUsers(Command):
    """Remove users from a group"""
    def get_parser(self, name):
        parser = super(GroupDelUsers, self).get_parser(name)
        parser.add_argument('groupname')
        parser.add_argument('--subtree',
                            default=self.app.default('group_tree', 'ou=Group'))
        parser.add_argument('username', nargs='+')
        return parser

    def take_action(self, args):
        conn = self.app.conn
        b = self.app.options.b
        groupname = args.groupname
        username = args.username
        context = args.subtree

        dn = 'cn=%s,%s,%s' % (groupname, context, b)
        mod_attrs = []
        for name in username:
            mod_attrs.append((ldap.MOD_DELETE, 'memberuid', name))
        conn.modify_s(dn, mod_attrs)


class GroupShow(Command):
    """Remove users from a group"""
    def get_parser(self, name):
        parser = super(GroupShow, self).get_parser(name)
        parser.add_argument('groupname')
        parser.add_argument('--subtree',
                            default=self.app.default('group_tree', 'ou=Group'))
        return parser

    def take_action(self, args):
        conn = self.app.conn
        b = self.app.options.b
        context = args.subtree
        groupname = args.groupname

        base_dn = '%s,%s' % (context, b)
        filter = '(cn=%s)' % groupname
        writer = LDIFWriter(sys.stdout)
        for dn, attrs in conn.search_s(base_dn, ldap.SCOPE_SUBTREE, filter):
            writer.unparse(dn, attrs)


def csep(s):
    "A utility function to split a comma separated string into a list"
    try:
        return s.split(',')
    except:
        raise ValueError("Illegal groups value")
