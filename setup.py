from setuptools import setup,find_packages
import glob

import subprocess, shlex

setup(
    name = 'kanone',
    version = '0.2',
    description='a validation library',
    author = 'don`catnip',
    author_email = 'don dot t at pan1 dot cc',
    url = 'http://github.com/doncatnip/require',
    packages = find_packages('src'),
    package_dir={'':'src'},
    install_requires = [ "zope.interface" ],
    #namespace_packages=['require' ],
    include_package_data=True,
)
