# Obol: useradd for ldap.

Obol is a command line utility to add, delete and modify users and
groups in an LDAP server.

Perhaps the most common use of LDAP is as a centralised store for
usernames and passwords. The protocol for managing an LDAP server
is somewhat verbose. It is cumbersome to create an LDIF file to 
modify a user attribute. 

For UNIX passwords, user and group management can be done using simple
command line tools like useradd and groupadd. Obol was created to 
provide a similar interface, but to manage users and groups inside an
LDAP server.

[![Build Status](https://travis-ci.org/hansthen/obol.svg?branch=master)](https://travis-ci.org/hansthen/obol)

© 2016 Hans Then. Obol is released under GPLv3.
see `gpl.txt` for details.
