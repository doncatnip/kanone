import pprint
import require

# require - stateful validation

#*************
#  example 1: the obvious
#_______

Hello = require.String() & require.Match('world')

#*************
#  example 2: using tags
#_______

Hello = Params( Integer.tag('integer') & Field('isInt',Set(value=True)) | String(strip=True,update=True) )

MoreHello = Params( Hello( integer_strict=True ) & ( Field( 'isInt', value=Match(True) )  & Pass()  ) | Email.tag('mail') )

hello = MoreHello( mail_domainPart_resolve=True )

context = hello( 10 )
print context.value
print context.result
print context('isInt').value

context.value = '  bob@lixum.net'
print context.value
print context.result
print context('isInt').value

"""
#*************
#  example 2: schema definition
#_______

# define some validator for later use
# note: * there are of course default error messages,
#         this is just for show ...
#       * if you don't use update=True, field.value remains
#         unchanged (e.g. unstripped) but field.result will 
#         still be whatever the validator returns


# this schema actually takes a string as input and returns one ...


myMail = Email\
    ( update_enabled=False
    , domainPart_restrictTLD = [ 'com', 'net', 'org' ]
    , domainPart_resolve = True
    ).error( input_blank='And your email address ?!' )


 
# define the schema
class Person( Schema ):

    messages( fail='Please try again :)' )

    fieldset\
        ( 'name'
        ,   ( String(strip=True,update=True).error\
                    ( blank="Please enter your name"
                    )
            & Len(min=2,max=20).error\
                    ( min="Name too short"
                    , max="Name too long"
                    )
            )

        , 'email'
        ,   email.clone( resolve=False ).error\
                ( invalid="That's just not possible !"
                )
        )

# Wait, that name field looks ugly ..
# can't we have all errors defined in one go ?
# Yes. But for that, we have to use 'tags', so that this And validator
# knows what validator did threw the error


## using tags ##

# define the schema
class Person( Schema ):

    messages( fail='Please try again :)' )

    fieldset\
        ( 'name'
        ,   ( String(strip=True).tag('str')
            & Len(min=2,max=20).tag('len')
            ).error\
                ( str_blank="Please enter your name"
                , len_min="Name too short"
                , len_max="Name too long"
                )

        , 'email'
        ,   email.clone( resolve=False ).error\
                ( invalid="That's just not possible !"
                )
        )


# note: you only need to clone() your validator, if you want to alter
# parameters, errors or want to use tag() otherwise just use the existing one


# init context with some default values
context = personSchema( [ 'bob' ] )

## context navigation ##

# A context is one node of a tree structure.
# What you get here is the root context for your schema, which is
# also acceccible as context.root from any child context. Also, every child
# has a .parent.
#
# context('myField') allways returns a child context. It does not neccisarily
# have a validator set, in which case you will get an error if you try to access
# context.result. context.value does atleast return require.MISSING with
# a '' str representation.
#
# If there are nested schemas involved, you can specify the full path like
# context('path.to.my.field').
#
# A context is a dict, which makes it easily iterable and serializable.

# after initialization, you can access default values easily
pprint.pprint( context('name').value )
pprint.pprint( context('email').value )

# errors are not here, as it's not yet validated
pprint.pprint( context('email').error )


## Validate single fields
try:
    pprint.pprint( context('email')).result
except Invalid,e:
    pprint.pprint( e )
    # now we should have an error here
    pprint.pprint( context('email')).error

# note: results and errors are cached and the context allways raises an
# error if there was one when your access .result


# use a custom error formatter

def myErrorFormatter( context, error):
    return ('%(path)s: '+error.msg) % ( error.extra )

context.errorFormatter = myErrorFormatter

pprint.pprint( context('email').error )


## More Validation ##

# ofc, you can set fields directly before validating them
context('email').value = '   Bob@Lixum.net'

# if you use update=True on a validator which supports it
# the input value will get updated as soon as you access it (again cached)
pprint.pprint( context('email').value )

# since we have set a new value, the context for 'email' was cleared
# you can also use context.clear() to force that behavior
pprint.pprint( context('email').error )


# validate the whole context
try:
    result = context.result
except Invalid,e:
    print "\nErrors:"
    print "=============\n"
    pprint.pprint( e )
    pprint.pprint( e.extra.errors )
else:
    print "\nResult:"
    print "=============\n"
    pprint.pprint ( result )
finally:
    print "\nFields:"
    print "=============\n"

    pprint.pprint( context('name') )
    pprint.pprint( context('email') )



#*************
#  example 3: combine schemas using schema.Merge
#_______


## Definitions ##

# define some schema
class EmailConfirm( Schema ):

    fieldset\
        ( 'email_confirm'
        ,   ( String(strip=True)
            & Match( Field('.email'), ignore_case=True ).error
                    ( missmatch="Entered value does not match your email address"
                    )
            ).error
                ( blank="Please retype your email address"
                )
        )

# note: The Field validator has access to any field within the context.
# To navigate relative from the current schema use . in the beginning,
# otherwise the field is relative to root.
# use .. to jump to the parent context ... parent of parent, etc


# instantiate the schema
# (note: order matters only if you're working with lists as input)
personSchema = Person() + EmailConfirm()


## Validation ##

# init context with some posted values
context = personSchema( [ 'bob','bob@lixum.net', 'bob@lixum.net'] )

# validate within that context
try:
    result = context.validate()
except Invalid,e:
    print "\nErrors:"
    print "=============\n"
    pprint.pprint( e )
else:
    print "\nResult:"
    print "=============\n"
    pprint.pprint ( result )

finally:
    print "\nFields:"
    print "=============\n"
    pprint.pprint( context('name') )
    pprint.pprint( context('email') )
    pprint.pprint( context('email_confirm') )
"""
