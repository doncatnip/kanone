from setuptools import setup,find_packages
import glob

setup(
    name = 'require',
    version = '0.0',
    description='a validation library',
    author = 'don`catnip',
    author_email = 'don.t@pan1.cc',
    url = '',
    packages = find_packages('src'),
    package_dir={'':'src'},
#    namespace_packages=['require' ],
    include_package_data=True,
)
