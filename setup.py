from setuptools import setup,find_packages
import glob

setup(
    name = 'require',
    version = '0.0',
    description='a validation library',
    author = 'defaultnick',
    author_email = 'schulzen@hostloco.com',
    url = 'hostloco.com',
    packages = find_packages('src'),
    package_dir={'':'src'},
#    namespace_packages=['require' ],
    include_package_data=True,
)
