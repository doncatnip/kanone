import pprint
from require import *

def failed(context):
    pprint.pprint ( context.pack() )

class TestSchema( Schema ):

    fieldset\
        ( ( 'name',     String() )
        , ( 'surname',  String() )
        , ( 'fullname', Field( '(this).name' ) )
        , ( 'testme',   Field( 'testme' ) )
        )


class EmbedTest( Schema ):
    fieldset\
        ( ( 'fields',   ForEach(TestSchema() ) )
        , ( 'testme',   Integer() )
        )

testSchema = EmbedTest()


post = [ [ [ 'bob', 'kranich' ] ], '42' ]

context = Context( post )
result = testSchema( context, errback=failed )

pprint.pprint ( result )
