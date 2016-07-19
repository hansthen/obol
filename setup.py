from setuptools import setup
import os

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
  name = 'obol',
  version = '2.0.3',
  description = 'useradd for ldap',
  author = 'Hans Then',
  author_email = 'hans.then@gmail.com',
  url = 'https://github.com/hansthen/obol',
  download_url = 'https://github.com/hansthen/obol/tarball/2.0',
  keywords = ['useradd', 'groupadd', 'ldap'],
  license = 'GPLv3',
  long_description=read('README.rst'),
  packages = ['obol'],
  classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
  ],
  entry_points={
          'console_scripts': [
              'obol = obol.main:main'
          ]
  },
  install_requires = [
     'python-ldap',
     'ldif3',
     'retrying',
     'cliff'
  ]
)
