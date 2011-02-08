import pprint
from require import *

def failed(context):
    print "\nErrors:"
    print "=============\n"
    pprint.pprint ( context.pack() )

class TestSchema( Schema ):

    fieldset\
        ( ( 'name',         String() )
        , ( 'surname',      String() )
        , ( 'email',        web.Email() )
        , ( 'email_confirm',Match(Field('(this).email')) )
        , ( 'schematest_amount',    Field( 'amount' ) )
        )


class EmbedTest( Schema ):
    fieldset\
        ( ( 'people',   ForEach(TestSchema() ) )
        , ( 'amount',   Integer() )
        )

class EmbedTestHtml( Schema ):
    pre_validate( web.NestedPost() )

    fieldset\
        ( ( 'people',   ForEach(TestSchema() ) )
        , ( 'amount',   Integer() )
        )


testSchema = EmbedTest() | EmbedTestHtml()



## native use (nested arrays or dicts)

post_native = [ [ [ 'bob', 'kranich','muh@lixum.net','muh@lixum.net' ], {'name':'fred','surname':'frith','email':'bob@lixum.net', 'email_confirm':'bob@lixum.net'} ], 42 ]

context = Context( post_native )

result = testSchema( context, errback=failed )

print "\nResult:"
print "=============\n"
pprint.pprint ( result )


## html post (field names represent nesting)

post_html = \
    { 'people.0.name':'bob'
    , 'people.0.surname':'kranich'
    , 'people.0.email':'muh@lixum.net'
    , 'people.0.email_confirm':'muh@lixum.net'
    , 'people.1.name':'fred'
    , 'people.1.surname':'frith'
    , 'people.1.email':'fred@lixum.net'
    , 'people.1.email_confirm':'fred@lixum.net'
    , 'amount': 42
    }


context = Context( post_html )

result = testSchema( context, errback=failed )

print "\nHTML Result:"
print "=============\n"
pprint.pprint ( result )
