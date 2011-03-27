require - validation library
============================

Why another validation lib ?

* there is a validation state represented as 'Context' throughout the
  validation process, which stores the current result for a certain field
  ( e.g. no validator will be called twice within a validation process )

* navigation through your data is very easy, once you have created a Context
  by using context( 'my.child.context' )

* You do not need to maintain a certain order for Fields which are depending
  on other fields, because validation takes place on demand.
  ( e.g. this will work:
    fieldset\
        ( 'email_confirm' , Match( Field('.email') )
        , 'email' , String()
        )
  )

* relative access by path of Fields within Schemas
  ( Field('..someChild') gets the value of a child called someChild of
    the parent context )

* Schemas and derivants can handle lists natively, because fields do have
  an order - enabling them to handle \*args


for more, see tutorial/tutorial.py for now
