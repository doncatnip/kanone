import pprint
from require import *


#*************
#  example 1: the obvious
#_______

hello = String(strip=True)
print hello( ' Hello World ! ' ).result


#*************
#  example 2: a basic schema
#_______


class Person( Schema ):

    messages( fail='Please try again :)' )

    fieldset\
        ( 'name'
        ,   ( String(strip=True).update()
            & Len(min=2,max=20).error\
                    ( min="Name too short"
                    , max="Name too long"
                    )
            ).error\
                ( blank="Please enter your name"
                )

        , 'email'
        ,  web.Email(strip=True,lower=True).update().error\
           ( format="Invalid email format"
           , localpartFormat="The part before @ (%(localpart)s) contains invalid symbols"
           , domainFormat="Domain %(domain)s contains invalid symbols"
           , domainResolve="Domain %(domain)s is invalid or does not exist"
           , blank="Please enter your email address"
           )
        )

    # just because we can ...
    post_validate( Call( lambda context, value: pprint.pprint("Validation done.\n") ) )


# instantiate the schema
personSchema = Person()

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

# errors are not here, as its not yet validated
pprint.pprint( context('email').error )


## Validate single fields
try:
    pprint.pprint( context('email').result
except Invalid,e:
    pprint.pprint( e )
    # now we should have an error here
    pprint.pprint( context('email').error )

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

# if you use update() on a validator which supports population,
# the input value will get updated as soon as you access them (again cached)
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



"""
#*************
#  example 3: combine schemas using schema.Merge
#_______


## Definitions ##

# define some schema
class EmailConfirm( Schema ):

    # if you don't use update(), field.value remains unchanged (e.g. unstripped)
    # but field.result will still be whatever the validator returns
    fieldset\
        ( 'email_confirm',  ( String(strip=True)
                            & Match( Field('(this).email'), ignore_case=True ).error
                                    ( missmatch="Entered value does not match your email address"
                                    )
                            ).error
                                ( blank="Please retype your email address"
                                )
        )

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

