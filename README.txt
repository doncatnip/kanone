Aims to provide a comfortable way to validate any kind of input by defining
a clonable base ( similar to what formencode does ), implementing a set of
atomic validators like And, Or, Not, Len, Strip etc. and a way to 'Compose' new
validators from existing ones.

Maintains a serializable state called 'Context' throughout each valditation
process which allows storing of input dependant metadata and provides
"validation on demand". The Context can also be used to populate forms or to set
request specific parameters.

Please visit https://github.com/doncatnip/kanone for more information.
