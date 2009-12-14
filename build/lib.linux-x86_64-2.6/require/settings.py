from pyped.util.utypes import Pulp
from .error import Invalid

text = Pulp()

text.Validator.info     = "Field cannot be empty nor missing"

text.Validator.msg      = ( "Please enter a value"
                          , "Please enter a value"
                          )

text.Empty.info         = "Must be missing or left blank"
text.Empty.msg          = "Field is given"

text.Missing.info       = "Must be missing"
text.Missing.msg        = text.Empty.msg

text.Blank.info         = "Must be left blank"
text.Blank.msg          = text.Empty.msg

text.Match.info         = "Must match %(required)s"
text.Match.msg          = "Value does not match"

text.Not.info           = "Must not met the criteria"
text.Not.msg            = "Criteria met"

text.Or.info            = "At least one criteria must be met"
text.Or.msg             = "No criteria met"

text.And.info           = "All criterias must be met"

text.Domain.info        = "Valid domain name"
text.Domain.msg         = ( 'Invalid TLD'
                        , 'No subdomains allowed' 
                        , 'Maxumum allowed subdomains: %(subdomain_max)'
                        , 'Domain contains invalid characters'
                        )

text.Boolean.info       = "Must be a boolean"

text.String.info        = ( "Must be a string"
                         , "A string with a minimum length of %(len_min)s is required"
                         , "A string with a maximum length of %(len_max)s is required"
                         , "A string with a length between %(len_min) and %(len_max)s is required"
                         )

text.String.msg       = (  "Entered value is not a string"
                         , "The string is too short"
                         , "The string is too long"
                         )

text.Integer.info       = ( "Must be a number"
                         , "A number greater than or equal to %(min)s is required"
                         , "A number smaller than or equal to %(max)s is required"
                         , "A number between %(min) and %(max)s is required"
                         )

text.Integer.msg      = ( "The entered value is not a number"
                         , "The number is too small"
                         , "The number is too big"
                         )

text.Dict.info          = "Must be a dictionary"
text.Dict.msg           = "Received value is not a dictionary"

text.List.info          = "Must be a list"
text.List.msg         = "Received value is not a list"

text.Schema.info        = "A form containing the fields: %(fields)s"
text.Schema.msg       = ( "Too many arguments received"
                         , "Field is not allowed: %(field)s"
                         )

text.Field.info       =  ( "Field %(field)s is required"
                         , "Field %(field)s must met this criteria"
                         )

text.Field.msg        =  ( "Field %(field)s is missing"
                         , "Field %(field)s is invalid"
                         )

text.domain2puny.msg    =  "Domain %(domain)s contains invalid symbols"
text.resolve_domain.msg = "Domain %(domain)s is invalid or does not exist" 

text.Email.info         = ( "Must be a valid email"
                         , "Must be a valid email with reachable domain"
                         )

text.Email.msg        =  ( "Invalid email format"
                         , u'The part before @ (%(localpart)s) contains invalid symbols'
                         , text.domain2puny.msg
                         , text.resolve_domain.msg
                         )
