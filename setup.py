from setuptools import setup, find_packages

setup\
    ( name = 'kanone'
    , version = '0.4.6'
    , description = 'a validation library'
    , long_description = open('README.txt').read()
    , author = 'don`catnip'
    , url = 'http://github.com/doncatnip/kanone'
    , classifiers =\
        [ "Development Status :: 4 - Beta"
        , "Topic :: Software Development :: Libraries :: Python Modules"
        , "License :: Public Domain"
        , "Programming Language :: Python :: 2.7"
        , "Programming Language :: Python :: 3"
        , 'Intended Audience :: Developers'
        ]
    , license = 'Unlicense'
    , keywords = 'validation library form twisted stateful'

    , packages = find_packages('src')
    , package_dir = {'':'src'}
    , install_requires = [ ]
    , namespace_packages = [ ]
    , include_package_data = True
    )
