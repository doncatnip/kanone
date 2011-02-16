# core = Validators working with any kind of data
# basic = Basic types
# check = Additional checks
# alter = Generic manipulation
# schema = Working witch context childs


core.Validator
core.Pass
core.Missing
# Means the field can not be given. Most other validators ( beside And, Or and
# some other core validators) do raise Invalid('missing').
# One could use it to force the absense of a field on a certain criteria
# e.g. reason = Field( 'cancelAccount', ( Error() | Is(result=False) ) & Missing() )

core.Blank
# Aka None or '' on Strings (every validator can implements its on_blank method)
# other validators do normally raise Invalid('blank')

core.Empty # derives from Missing and Blank
core.Error  ( TODO ) # check if the context has an error
core.Abort  ( TODO )
# raises error='myError' if set, otherwise just abort and set result to original input 

core.And
core.Or
core.Not
core.Call
# calls func(context, value), you can raise require.error.Invalid('myError')
# to be able to set errormessages later

core.Tag
core.Tagger


basic.Integer
# use Integer.convert() to try to convert, otherwise it must be an instance of int or long
# ( Integer.convert() actually just instantiates Integer( convert=True) )

basic.Float     # same with float
basic.Strig     # unicode, str
basic.List      # list, tuple, set
basic.Dict      # dict, UserDict
basic.Boolean   # int, bool

# if you *really really* need to be that exact, use check.Is, but in most cases
# you don't want to

check.Match # works with string, re and other validators.
check.Is    ( TODO )
# e.g. Is(value=u'mäh'), Is(result=u'muh') or Is(instanceOf=unicode)
# unlike mach, the value needs to be exact, as it does not compare using
# str(value)==str(requirement) and has no ignoreCase parameter

check.In    ( TODO )
check.Len   ( TODO )
check.Range ( TODO )
# should work with int, float, long 


alter.Cut   ( TODO )
alter.Strip ( TODO )
alter.Lower ( TODO )
alter.Upper ( TODO )
alter.EliminateWhiteSpace (TODO )
alter.Split ( TODO )
alter.Join ( TODO )
alter.Update # writes back the current result to input


schema.Schema
schema.Merge (TODO)
schema.Field
schema.Set (TODO)
schema.Get (TODO)
schema.ForEach
# ForEach derives from schema, because it creates new context childs, accessible
# as context('my.field.[0..n]')


web.NestedPost
web.DomainLabel (TODO) # a single part (either the TLD or a subdomain, as they are following the same rules)
web.Domain  # uses Split, Foreach and DomainLabel
web.DomainLookup (TODO)
web.EmailLocalPart
web.Email   # uses Schema, Domain and EmailLocalPart
