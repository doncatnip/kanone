kanone - a validation library
=============================

Aims to provide a comfortable way to validate any kind of input by defining
a clonable base ( similar to what formencode does ), implementing a set of
atomic core validators and a way to 'Compose' new validators from existing
ones.

Maintains a serializable state called 'Context' throughout each valditation
process which allows storing of input dependant metadata and provides
"validation on demand".
The Context can also be used to populate forms or to set request specific
parameters.


# Why bother ?

* Navigation through your data is easily done using
  `context( 'my.child.context' )` once you have created a Context.

* You do not need to maintain a certain order for fields which are depending
  on other fields, because validation takes place on demand.
  E.g. this will work:

        Schema\
            ( 'email_confirm' , Match( Field('.email') )
            , 'email' , String()
            )

* Relative access by path of fields during validation
  ( Field('..someChild') retrieves the value from a child called someChild
    relative to the parent context; root can be addressed by using '/' ).

* Access to fields by index during validation ( `Field('.(0)')` will retrieve
  the value of the first field while `Field('.(-1)')` retrieves the last )

* Schemas can handle lists natively, because defined fields do have an order.
  One could use them to validate the \*varargs of a function or in chain after
  Split() and the like.

* Easy serialization of the whole context, containing errors and values which
  should be re-populated ( e.g. when your domain validator lowers the input ).
  Quite handy if you have some RPC service which validates raw form data
  submitted by an ajax call.

* IDNA-aware DomainLabel, Domain, and Email validator.

* experimental Twisted support via monkey patching: write asynchronous
  validators by simply returning Deferreds.

# Getting started

## Installation

    pip install kanone

## Because we all like Hello World's

1) create a Validator

    >>> from kanone import *
    >>> Hello = String() \
        & Tmp( alter.Lower() & In( ['world', 'bob'] ) ) \
        & alter.Format('Hello %(value)s !')

*Note*: The `Tmp` validator means: do not return the result. 
In this case, `In` uses the result of `alter.Lower`, while the input value
for `alter.Format` remains unmodified.

2) bring the validator and a value into a context

    >>> context = Hello.context( 'World' )

3) get the result

    >>> context.result
    u'Hello World !'

set another value

    >>> context.value = 'Bob'

re-validate

    >>> context.result
    u'Hello Bob !'


## Basics

### Chaining, Alternation and Negation

Chaining: `And( Validator1, Validator2, ... )`,
shortcut: `Validator1 & Validator2 & ...`

Alternation: `Or( Validator1, Validator2, ... )`,
shortcut: `Validator1 | Validator2 | ...`

Negation: `Not( Validator )`, shortcut: `!Validator`

### Blank(), Empty() and Missing()

While most validation libraries have parameters to test for null values
or to allow a value to be missing, kanone has seperate Validators to do that.

Instead of something like String( required=False, default='' ) you'd write

    Empty('') | String()

*Blank* tests if the value is Null or ''  
*Missing* tests if the value is not given  
*Empty* tests if the value is either Missing or Blank

All of them accept a value as optional parameter which will be used as default.
If you pass a dict or list, the condition will also be met if the input value
is an empty dict or list respectiveley.


## Errors

    >>> context.value = 42
    >>> context.result
    Traceback ( most recent call last):
    ...
    kanone.error.Invalid: Invalid type (int), must be a string
    >>> context.error
    'Invalid type (int), must be a string'

### Custom error messages

    >>> Hello = String().messages\
            ( type='This is not a string, it is a "%(value.type)s" !'
            )\
        & Tmp\
            ( alter.Lower()
            & In\
                ( ['world', 'bob']
                ).messages\
                    ( fail='Please enter "bob" or "world", not "%(value)s".'
                    )
            )\
        & alter.Format('Hello %(value)s !')
    >>> Hello.context( 42 ).result
    Traceback (most recent call last):
    ...
    kanone.error.Invalid: This is not a string, it is a "int" !

### The errorFormatter

Error messages are generated on demand and after the validation process,
using an `errorFormatter`. One can use his own function - which, for example,
does the l13n stuff, or retrieves messages by a certain error ID.

    >>> context.errorFormatter = lambda context, error:\
        ("Error at %s: %s" % (context.path, error.message ) ) % error.extra
    >>> context.error
    'Error at /: Invalid type (int), must be a string'


## Composing

Composing is useful if you want to create reusable Validators from existing
ones. You can *tag* the containing validators to make them adjustable.
Set parameter/message aliases to combine different tags.

*Note*: Please take a look at `kanone.validator.web` for advanced
tag usage, since `DomainLabel`, `Domain`, `EmailLocalPart`, `Email` and
`DateField` are all composed.

    >>> Hello = Compose\
        ( String().tag('inputType')
        & debug.Print('Entered: %(value)s').tag('printInput',False)
        & Tmp\
            ( alter.Lower()
            & In\
                ( ['world', 'bob']
                ).tag('restrictInput')
            )
        & alter.Format('Hello %(value)s !').tag('output')
        ).paramAlias\
            ( restrict='restrictInput_criteria'
            )\
         .messageAlias\
            ( restrict='restrictInput_fail'
            )

*Note*: An alias points to a [tagName]_[parameterName] or to a list of them or
to a function returning a list of them. Every tag has an 'enabled' parameter.
You can set a tag to be disabled by default with .tag('tagName',False)

    >>> myHello = Hello\
        ( restrict=['there','bob']
        , output_formatter='Hey %(value)s !'
        , printInput_enabled=True
        ).messages(restrict='Please enter one of %(criteria)s')
    >>> context = myHello.context( 'there' )
    >>> context.result
    Entered: there
    u'Hey there !
    >>> context.value = 'world'
    >>> context.result
    Entered: world
    Traceback (most recent call last):
    ...
    Invalid: Please enter one of ['there', 'bob']


## Custom Validators

    >>> @messages( wrong='Wrong answer ! %(question)s' )
    ... class Quiz( Validator ):
    ...
    ...     def setParameters( self, question, answer ):
    ...         self.question = question
    ...         self.answer = answer
    ...
    ...     def on_value( self, context, value ):
    ...         if value != self.answer:
    ...             raise Invalid\
    ...                 ( value, self, 'wrong', question=self.question )
    ...         return value
    ...
    >>> q = Quiz( 'Life, the Universe and Everything ?', 42 )
    >>> q.context( 43 ).result
    Traceback (most recent call last): 
    ...
    kanone.error.Invalid: Wrong answer ! Life, the Universe and Everything ?
    >>> cheat = q( answer=43 )
    >>> cheat.context( 43 ).result
    43

Possible method overrides:

* `validate( self, context, value)`  
  Will allways be called. Override this if you have no need to filter
  blank or missing values. Returns a value or raises Invalid.

* `on_value( self, context, value)`  
  Will be called if a value is given and it is not None or ''. Returns a value
  or raises Invalid.

* `on_blank( self, context, value)`  
  Will be called if the value is None or ''. Raises Invalid with type 'blank'.

* `on_missing( self, context)`  
  Will be called if the value is missing. Raises Invalid with type 'missing'.

*Note*: Parameters which are defined in setParameters are adjustable when tagged
or cloned. Use setArguments to set immutable arguments.


## Schemas

A `Schema` takes dicts or list-likes as input and will return a dict, or a list
if used with returnList=True.

*Note*: please take a look at kanone.validator.web.Email for some real-world
example

    >>> HelloSchema = Schema\
        ( 'nick'
            , String() & Len(max=20)
        , 'email'
            , web.Email()
        , 'email_confirm'
            , Match( Field('.email'), ignoreCase=True )
        )
    >>> context = HelloSchema.context\
        (   { 'nick':'bob'
            , 'email':'Bob@Some.Domain.Org'
            , 'email_confirm': 'BOB@Some.domain.org'
            }
        )
    >>> context('nick').result
    u'bob'
    >>> context('email').result
    u'Bob@some.domain.org'

    >>> from pprint import pprint
    >>> pprint( context.result )
    {'email': u'Bob@some.domain.org',
    'email_confirm': 'BOB@Some.domain.org',
    'nick': u'bob'}

Provide a list as input

    >>> context = HelloSchema.context\
        (   [ 'bob'
            , 'Bob@Some.Domain.Org'
            , 'BOB@Some.domain.org'
            ]
        )
    >>> pprint( context.result )
    {'email': u'Bob@some.domain.org',
    'email_confirm': 'BOB@Some.domain.org',
    'nick': u'bob'}


*Note*: The domain part will be lowered ( local part is case-sensitive
acc. to specs )
you can disable this behaviour with `Email(domainPart_toLower=False)`

###  Nested Schemas

    >>> NestedSchema = Schema\
        ( 'people'
            , ForEach( HelloSchema ) & Len( max=2 )
        )

*Note*: ForEach creates new context children ( as well as Schema ),
use ForEach( createContextChildren=False ) to disable this behaviour.

    >>> context = NestedSchema.context\
        (   { 'people':\
                [   { 'nick': 'bob'
                    , 'email': 'Bob@Some.Domain.Org'
                    , 'email_confirm': 'BOB@Some.domain.org'
                    }
                ,   { 'nick': 'jack'
                    , 'email': 'Jack@Some.Domain.Org'
                    , 'email_confirm': 'JACK@Some.domain.org'
                    }
                ]
            }
        )
    context('people.0.nick').result
    'bob'
    context('people.0.email').result
    'Bob@some.domain.org'
    context('people.0.email_confirm').result )
    'BOB@Some.domain.org'
    >>>
    >>> context.value = \
        ( [ { 'email':'Bob@Some.Domain.Org','email_confirm':'BOB@Some.domain.or' } ] )
    >>> try:
    ...     result = context.result
    ... except Invalid as e:
    ...     print (context.errorlist)
    ['/people.0.nick', '/people.0.email_confirm' ]

*Note*: Errors will only be appended to the errorList if the message is not
None. Schema and ForEach do have None set as 'fail' message, thus do not
populate the context with an error by default.

    >>> context( 'people.0.nick' ).error
    'Please provide a value'
    >>> context( 'people.0.email_confirm' ).error
    'Value must match bob@some.domain.org'

### HTTP POST friendly Schemas

    >>> NestedForm = web.NestedPost() & NestedSchema
    >>> context = NestedForm.context\
        (   { 'people.0.nick':'bob'
            , 'people.0.email':'Bob@Some.Domain.Org'
            , 'people.0.email_confirm': 'BOB@Some.domain.org'
            , 'people.1.nick':'jack'
            , 'people.1.email':'Jack@Some.Domain.Org'
            , 'people.1.email_confirm': 'JACK@Some.domain.org'
            }
        )
    >>> context.result
    {'people': [{'email': u'Bob@some.domain.org',
                 'email_confirm': 'BOB@Some.domain.org',
                 'nick': u'bob'},
                {'email': u'Jack@some.domain.org',
                 'email_confirm': 'JACK@Some.domain.org',
                'nick': u'jack'}]}


##  (json) serialization

This is farly easy, since a context is a native dict.

    >>> pprint( context )
    {{{ lots of pretty printed stuff, you should see for yourself }}}
    >>> import json
    >>> json.dumps( context )
    {{{ lots of not so pretty printed stuff }}}


## Using decorators to validate Python functions

    >>> from kanone.adapter.native import validate
    >>> from pprint import pprint
    >>> @validate\
    ...     ( Schema\
    ...         ( 'someString', Missing('bob') | String()
    ...         , 'someInt', Integer()
    ...         , 'numbers', Blank([]) | Len(min=3) & ForEach( Integer() )
    ...         , 'params', Blank({}) | Len(max=3)\
    ...             & ForEach( String(), numericKeys=False, returnList=False )
    ...         )
    ...     , exclude=('skipMe',)
    ...     )
    ... def someFunc( skipMe, someString, someInt, *numbers, **params ):
    ...     pprint (someString)
    ...     pprint (someInt)
    ...     pprint (numbers)
    ...     pprint (params)

*Notes*:

* You could also use a Schema instead of ForEach, it just have to return a list
  when used with `*varargs` or a dict when used with `**kwargs`
* The order does not matter in the root Schema, as the function will be
  inspected to convert any input `*args, **kwargs` into a dict.
* Use `exclude`/`include` to exclude/include arguments from being validated.
  vararg and kwarg names can also be specified here.
* Use `onInvalid` to specify an error callback. The signature of the error
  function is ( context, error ). It should raise an error or return a value.

Test that function:

    >>> someFunc( 'skipped', someInt=1 )
    'bob'
    1
    ()
    {}

    >>> someFunc( 'skipped', 'jack', 42, 3, 2, 1 )
    u'jack'
    42
    (3, 2, 1)
    {}

    >>> someFunc( 'skipped', someInt=42, param1='p1', param2='p2' )
    'bob'
    42
    ()
    {'param1': u'p1', 'param2': u'p2'}

    >>> someFunc( 'skipped', 'jack', 42, 3, 2 )
    Traceback (most recent call last):
    ...
    kanone.error.Invalid: Invalid(
        { 'someString': 'jack', 'someInt': 42, 'numbers': [3, 2]
        , 'params': {}}, fail )

### Decorate Pylons actions

You can find a Pylons example app in examples/pylons.


## Twisted

    >>> from kanone.adapter import tx
    >>> tx.monkeyPatch()

From now on, context.validate() and context.result are returning Deferreds.
Schema and ForEach are validating their fields concurrently if possible.

If you need a method decorator, use

    >>> from kanone.adapter.tx import validate

It behaves similar to the native validate decorator described above, but will
always return a deferred. Pass `inlineCallbacks=True` to the decorator in order
to use twisted's inlineCallbacks within a validated method.
