from setuptools import setup,find_packages
import glob

import subprocess, shlex

p = subprocess.Popen(shlex.split('git describe'),stdout=subprocess.PIPE)
(appVersion, error) = p.communicate(  )

setup(
    name = 'require',
    version = appVersion.decode('ascii')[0:-1],
    description='a validation library',
    author = 'don`catnip',
    author_email = 'don.t@pan1.cc',
    url = '',
    packages = find_packages('src'),
    package_dir={'':'src'},
    install_requires = [ "zope.interface" ],
#    namespace_packages=['require' ],
    include_package_data=True,
)
