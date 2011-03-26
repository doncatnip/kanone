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
pprint( context.error )

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
    context.errorFormatter = lambda context, error: ('"%(value)s" is not allowed here' % error.extra)
    pprint (str(e))      # '"there" not allowed here'

# use catchall to set a message for every possible error

Hello = ( require.String() \
        & require.Tmp\
            ( require.alter.Lower()
            & require.check.In\
                ( ['world', 'bob']
                )
            ) \
        & require.alter.Format('Hello %(value)s !')
        ).messages(catchall='Please enter "bob" or "world", not "%(value)s".')

context = require.Context( Hello, None )

try:
    result = context.result
except require.Invalid as e:
    pprint (str(e))      # 'Please enter "bob" or "world", not "None".'


#*************
#  example 4: composing
#_______

# composing is useful if you want to reuse a certain validator with different
# parameters or messages

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

