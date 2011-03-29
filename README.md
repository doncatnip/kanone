require - validation library
============================

Why another validation lib ?

* There is a validation state represented as *Context* throughout the
  validation process, which stores the current result for a certain field
  ( e.g. no validator will be called twice within a validation process )

* Navigation through your data is easily done using context( 'my.child.context' )
  once you have created a Context.

* You do not need to maintain a certain order for Fields which are depending
  on other fields, because validation takes place on demand.
  ( e.g. this will work:
        fieldset\
            ( 'email_confirm' , Match( Field('.email') )
            , 'email' , String()
            )
  )

* Relative access by path of Fields during validation
  ( Field('..someChild') gets the value of a child called someChild of
    the parent context; root can be addressed by using '/' ).

* Access fields by index during validation ( Field('.(0)') will get you the
  value of the first field, Field('.(-1)') will address the last )

* Schemas can handle lists natively, because defined fields do have an order.
  One could use them to validate the \*varargs of a function or in chain after
  Split() and the like.

* Easy serialization of the whole context, containing errors and values which
  should be re-populated ( e.g. when your domain validator lowers the input ).

* Punycode-aware DomainLabel, Domain, and Email validator.

for more, see tutorial/tutorial.py for now
