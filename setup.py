from setuptools import setup,find_packages
import glob

import subprocess, shlex

setup(
    name = 'kanone',
    version = '0.3',
    description='a validation library',
    description_long=open('README.txt').read(),
    author = 'don`catnip',
    author_email = 'don dot t at pan1 dot cc',
    url = 'http://github.com/doncatnip/kanone',
    packages = find_packages('src'),
    package_dir={'':'src'},
    install_requires = [ "zope.interface" ],
    #namespace_packages=['kanone' ],
    include_package_data=True,
)
