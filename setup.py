from distutils.core import setup
setup(
  name = 'obol',
  scripts = ['obol'],
  version = '1.2',
  description = 'useradd for ldap',
  author = 'Hans Then',
  author_email = 'hans.then@gmail.com',
  url = 'https://github.com/hansthen/obol', # use the URL to the github repo
  download_url = 'https://github.com/hansthen/obol/tarball/1.2', # I'll explain this in a second
  keywords = ['useradd', 'groupadd', 'ldap'], # arbitrary keywords
  classifiers = [],
  install_requires = [
     'python-ldap',
     'ldif3',
     'retrying',
  ]
)
