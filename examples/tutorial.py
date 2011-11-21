from pprint import pprint
from kanone import *

## use this to test twisted 'mode'
## it should work even without a running reactor or callbacks
## Except that results are encapsuled in Deferreds and errors
## are not catched, but printed as unhandled Faults instead.
#
# from require.adapter import tx
# tx.monkeyPatch()


# require - stateful validation


#*************
#  example 1: the obvious
#_______

# 1) create a Validator
Hello = String() \
        & Tmp( alter.Lower() & In( ['world', 'bob'] ) ) \
        & alter.Format('Hello %(value)s !')

# 2) bring the validator and a value into a context
context = Context( Hello, 'World' )

# 3) get the result
pprint ( context.result ) # Hello World !

# set another value
context.value = 'Bob'

# re-validate
pprint ( context.result ) # Hello Bob !



#*************
#  example 2: errors
#_______

context.value = 42

try:
    result = context.result
except Invalid as e:
    pprint (str(e))      # Invalid type (int), must be a string

# the context now holds the error as string
pprint( context.error )  # Invalid type (int), must be a string



#*************
#  example 3: error messages
#_______

Hello = String().messages(type='This is not a string, it is a "%(value.type)s" !') \
        & Tmp\
            ( alter.Lower()
            & In\
                ( ['world', 'bob']
                ).messages(fail='Please enter "bob" or "world", not "%(value)s".')
            ) \
        & alter.Format('Hello %(value)s !')

context = Hello.context( 'there' )

try:
    result = context.result
except Invalid as e:
    pprint (str(e))      # 'Please enter "bob" or "world", not "there".'

    # you can change the errorFormatter at any time
    context.errorFormatter \
        = lambda context, error: (('Error (%(value.type)s): '+error.message) % error.extra)
    pprint (str(e))      # 'Error (unicode): Please enter "bob" or "world", not "there".' 



#*************
#  example 4: composing
#_______

# composing is useful if you want to reuse a certain validator with different
# parameters or messages

# note: please take a look at require.validator.web for advanced
# tag usage, since DomainLabel, Domain, EmailLocalPart and
# Email are all composed

Hello = Compose\
        ( String().tag('inputType') \
        & debug.Print('Entered: %(value)s').tag('printInput',False) \
        & Tmp\
            ( alter.Lower()
            & In\
                ( ['world', 'bob']
                ).tag('restrictInput')
            ) \
        & alter.Format('Hello %(value)s !').tag('output')
        ).paramAlias\
        ( restrict='restrictInput_required'
        ).messageAlias\
        ( restrict='restrictInput_fail'
        )

# note: an alias is a [tagName]_[parameterName] or a list of them
# or a function returning a list of them

myHello = Hello\
        ( restrict=['there','bob']
        , output_formatter='Hey %(value)s !'
        , printInput_enabled=True
        ).messages(restrict='Please enter one of %(required)s')

context = myHello.context( 'there' ) 

pprint (context.result ) # 'Hey there !'

context.value = 'world'

try:
    result = context.result
except Invalid as e:
    pprint (str(e))      # 'Please enter one of ['there', 'bob']'



#*************
#  example 5: schemas
#_______

# note: please take a look at require.validator.web.Email for a
# more advanced real-world example

HelloSchema = Schema\
    ( 'nick'
        , String() & Len(max=20)
    , 'email'
        , web.Email()
    , 'email_confirm'
        , Match( Field('.email'), ignoreCase=True )
    )

context = Context\
    ( HelloSchema
    ,   { 'nick':'bob'
        , 'email':'Bob@Some.Domain.Org'
        , 'email_confirm': 'BOB@Some.domain.org'
        }
    )

pprint (context('nick').result ) # 'bob'
# note: the domain part will be lowered ( local part is case-sensitive acc. to specs )
# you can disable this behaviour by Email(domainPart_toLower=False)
pprint (context('email').result ) # 'Bob@some.domain.org'
pprint (context('email_confirm').result ) # 'BOB@Some.domain.org'


# you can also use a list as input, which is handy if you, for example, want
# to validate the *args of a function or after using Split() and thelike

context.value = ['jack','Jack@Some.Domain.Org', 'jack@Some.domain.org']

pprint (context('nick').result ) # 'jack'
pprint (context('email').result ) # 'Jack@some.domain.org'
pprint (context('email_confirm').result ) # 'jack@Some.domain.org'



#*************
#  example 6: nested (and posted) schemas
#_______


PostedSchema = \
    ( web.NestedPost()
    & debug.Print('Nested: %(value)s')
    & Schema\
        ( 'people'
            , ForEach( HelloSchema )
        )
    )

# notes:
# * ForEach creates new context childs ( as well as Schema )
#   use ForEach( createContextChilds=False ) to disable this behaviour
# * you could just remove NestedPost and use native nested dicts
#   as input, or you can set the values of childs manually - e.g.:
#   context('people.0.nick').value = 'bob'


context = Context\
    ( PostedSchema
    ,   { 'people.0.nick':'bob'
        , 'people.0.email':'Bob@Some.Domain.Org'
        , 'people.0.email_confirm': 'BOB@Some.domain.org'
        , 'people.1.nick':'jack'
        , 'people.1.email':'Jack@Some.Domain.Org'
        , 'people.1.email_confirm': 'JACK@Some.domain.org'
        }
    )

pprint (context('people.0.nick').result ) # 'bob'
pprint (context('people.0.email').result ) # 'Bob@some.domain.org'
pprint (context('people.0.email_confirm').result ) # 'BOB@Some.domain.org'

pprint (context('people').result )
#[{'email': u'Bob@some.domain.org',
#  'email_confirm': 'BOB@Some.domain.org',
#  'nick': u'bob'},
# {'email': u'Jack@some.domain.org',
#  'email_confirm': 'JACK@Some.domain.org',
#  'nick': u'jack'}]


context.value = \
    { 'people.0.email':'Bob@Some.Domain.Org'
    , 'people.0.email_confirm': 'BOB@Some.domain.or'
    }

try:
    result = context.result
except Invalid as e:
    pprint(context.errorlist) # ['/people.0.nick', '/people.0.email_confirm' ]
    # note: errors will only be set if the message is not None
    # Schema and ForEach do have None set as 'fail' message, thus do
    # not populate the context with an error by default

pprint ( context( 'people.0.nick' ).error )  # 'Please provide a value'
pprint ( context( 'people.0.email_confirm' ).error )  # 'Value must match bob@some.domain.org'


#*************
#  example 7: (json) serialization
#_______

# farly easy, since a context is a native dict
pprint ( context ) # '{ lots of pretty printed stuff }'

import json

pprint( json.dumps( context ) ) # '{ lots of not so pretty printed stuff }'


# TODO: there is much, much more to show :)



#*************
#  example 8: Using decorators to validate any python function
#_______


from require.adapter.native import validate

def onInvalid( error ):
    pprint( error.context )
    raise error

# notes:
# * you could also use a Schema instead of ForEach, it just have to return a list
# * the order does not matter in the root Schema, as the function will be inspected
#   to convert any input *args, **kwargs into a dict
@validate\
    ( Schema\
        ( 'someString', Missing('bob') | String()
        , 'someInt', Integer()
        , 'numbers', Empty([]) | Len(min=3) & ForEach( Integer() )
        )
    , onInvalid = onInvalid # optional - if not set, the error will just be raised
    )

def someFunc( someString, someInt, *numbers ):
    pprint (someString)
    pprint (someInt)
    pprint (numbers)


someFunc( someInt=1 )
# 'bob'
# 1
# ()

someFunc( 'jack', 42, 3, 2, 1 )
# u'jack'
# 42
# (3, 2, 1)

try:
    someFunc( 'jack', 42, 3, 2 )
except Invalid as e:
    pprint ( e )
    # Invalid({'*numbers': [3, 2], 'someString': 'jack', 'someInt': 42}, fail)


# does also work with **kwargs ( well, or both, *args and **kwargs )..

# note: you could also use a Schema instead of ForEach, it just have to return a dict
@validate\
    ( Schema\
        ( 'params', Empty({}) | Len(min=3)\
            & ForEach( Integer(), numericKeys=False, returnList=False )
        , 'someString', Missing('bob') | String()
        , 'someInt', Missing(42) | Integer()
        )
    , onInvalid = onInvalid # optional - if not set, the error will just be raised
    )
def someFunc( someString, someInt, **params ):
    pprint (someString)
    pprint (someInt)
    pprint (params)


someFunc( param1=1, param2=2, param3=3 )
# 'bob'
# 42
# {'param1': 1, 'param2': 2, 'param3': 3}

someFunc( 'jack', 22 )
# u'jack'
# 22
# {}

