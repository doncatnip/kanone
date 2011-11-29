from setuptools import setup, find_packages

setup\
    ( name = 'kanone'
    , version = '0.3.2'
    , description = 'a validation library'
    , long_description = open('README.txt').read()
    , author = 'don`catnip'
    , author_email = 'don dot t at pan1 dot cc'
    , url = 'http://github.com/doncatnip/kanone'
    , classifiers =\
        [ "Development Status :: 4 - Beta"
        , "Topic :: Software Development :: Libraries"
        ]
    , license = 'Unlicense'
    , keywords = 'validation library form twisted stateful'

    , packages = find_packages('src')
    , package_dir = {'':'src'}
    , install_requires = [ "zope.interface" ]
    #, namespace_packages = ['kanone' ]
    , include_package_data = True
    )
