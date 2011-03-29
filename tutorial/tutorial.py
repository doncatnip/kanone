from pprint import pprint
import require

# require - stateful validation



#*************
#  example 1: the obvious
#_______

# 1) create a Validator
Hello = require.String() \
        & require.Tmp( require.alter.Lower() & require.check.In( ['world', 'bob'] ) ) \
        & require.alter.Format('Hello %(value)s !')

# 2) bring the validator and a value into a context
context = require.Context( Hello, 'World' )

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
except require.Invalid as e:
    pprint (str(e))      # Invalid type (int), must be a string

# the context now holds the error as string
pprint( context.error )  # Invalid type (int), must be a string



#*************
#  example 3: error messages
#_______

Hello = require.String().messages(type='This is not a string, it is a "%(type)s" !') \
        & require.Tmp\
            ( require.alter.Lower()
            & require.check.In\
                ( ['world', 'bob']
                ).messages(fail='Please enter "bob" or "world", not "%(value)s".')
            ) \
        & require.alter.Format('Hello %(value)s !')

context = require.Context( Hello, 'there' )

try:
    result = context.result
except require.Invalid as e:
    pprint (str(e))      # 'Please enter "bob" or "world", not "there".'

    # you can change the errorFormatter at any time
    context.errorFormatter \
        = lambda context, error: (('Error (%(type)s): '+error.message) % error.extra)
    pprint (str(e))      # 'Error (unicode): Please enter "bob" or "world", not "there".' 


# use catchall to set a message for every possible error

Hello = ( require.String() \
        & require.Tmp\
            ( require.alter.Lower()
            & require.check.In\
                ( ['world', 'bob']
                )
            ) \
        & require.alter.Format('Hello %(value)s !')
        ).messages(catchall='Validation for "%(value)s", %(type)s) failed.')

context = require.Context( Hello, None )

try:
    result = context.result
except require.Invalid as e:
    pprint (str(e))      # 'Validation for "None", NoneType failed.'



#*************
#  example 4: composing
#_______

# composing is useful if you want to reuse a certain validator with different
# parameters or messages

# note: please take a look at require.validator.web for advanced
# tag usage, since DomainLabel, Domain, EmailLocalPart and
# Email are all composed

Hello = require.Compose\
        ( require.String().tag('inputType') \
        & require.debug.Print('Entered: %(value)s').tag('printInput',False) \
        & require.Tmp\
            ( require.alter.Lower()
            & require.check.In\
                ( ['world', 'bob']
                ).tag('restrictInput')
            ) \
        & require.alter.Format('Hello %(value)s !').tag('output')
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

context = require.Context( myHello, 'there' ) 

pprint (context.result ) # 'Hey there !'

context.value = 'world'

try:
    result = context.result
except require.Invalid as e:
    pprint (str(e))      # 'Please enter one of ['there', 'bob']'



#*************
#  example 5: schemas
#_______

# note: please take a look at require.validator.web.Email for a
# more advanced real-world example

class HelloSchema( require.Schema ):

    require.fieldset\
        ( 'nick'
            , require.String() & require.check.Len(max=20)
        , 'email'
            , require.web.Email()
        , 'email_confirm'
            , require.Match( require.Field('.email'), ignoreCase=True )
        )

context = require.Context\
    ( HelloSchema()
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

# note: you could just remove NestedPost and use native nested dicts
# as input, or you can set the values of childs manually - e.g.:
#   context('people.0.nick').value = 'bob'

class PostedSchema( require.Schema ):

    require.pre_validate\
        ( require.web.NestedPost()
        & require.debug.Print('Nested: %(value)s')
        )

    require.fieldset\
        ( 'people'
            , require.ForEach( HelloSchema() )
        )

# notes:
# * using pre_validate or post_validate results in an And validator
#   as you would have written
#     SomePreValidators() & MyValidator() & SomePostValidators()
# * ForEach creates new context childs ( as well as Schema )
#   use ForEach( createContextChilds=False ) to disable this behaviour


context = require.Context\
    ( PostedSchema()
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
except require.Invalid as e:
    pprint(context.errorlist) # ['/people.0.nick', '/people.0.email_confirm', '/people.0', '/people', '/']
    # note: if a child has an error, the parent also does

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
