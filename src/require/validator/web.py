import re

from ..lib import messages, pre_validate, post_validate, fieldset

from .core import ValidatorBase, Validator, Compose, Pass
from .basic import String, Dict
from .alter import Encode, Lower, EliminateWhiteSpace, Split, Join, UpdateValue, Insert
from .check import Match, Blank, In, Len
from .schema import Schema, ForEach, Field
from .debug import Print

import cache

class ResolveDomain( Validator ):

    messages\
        ( fail='Domain not found'
        )

    def on_value( self, context, value ):
        import DNS

        a=DNS.DnsRequest(value, qtype='mx').req().answers
        if not a:
            a=DNS.DnsRequest(value, qtype='a').req().answers

        dnsdomains=[x['data'] for x in a]
        if not dnsdomains:
            raise self.invalid( context )

        return value


CommonDomainPreValidaton\
    = String.convert().tag('string')\
    & EliminateWhiteSpace().tag('eliminateWhiteSpace')\
    & Lower().tag('toLower')\
    & UpdateValue().tag('update')


DomainLabel = Compose\
    ( CommonDomainPreValidaton().tag('prevalidation')
    & cache.Save(result='preEncode').tag('punycode')\
    &   ( Match( re.compile(r'^xn--') )\
        |   ( Encode('punycode')\
            &   (   (   Match( re.compile(r'.*-$') )\
                    &   cache.Restore(result='preEncode')\
                    )
                |   Insert('xn--',0)
                )
            )
        ).tag('punycode')
    & Len(max=63).tag('tooLong')
    & Match(re.compile(r'^(xn--)?[a-z0-9]+([-a-z0-9]+)*$')).tag('validSymbols')
    & cache.Restore(result='preEncode').tag('returnNonPuny', False)
    ).paramAlias\
        ( convertToString='string_convert'
        , updateValue='update_enabled'
        , eliminateWhiteSpace='eliminateWhiteSpace_enabled'
        , toLower='toLower_enabled'
        , convertToPunycode='punycode_enabled'
        , returnNonPuny='returnNonPuny_enabled'
    ).messageAlias\
        ( type='string_type'
        , tooLong='tooLong_fail'
        , invalidSymbols='validSymbols_fail'
        , blank=("toLower_blank","string_blank")
        , missing="string_missing"
    ).messages\
        ( blank='Please provide a value'
        , tooLong='A domain can have max %(max)i characters'
        , invalidSymbols='The domain name contains invalid symbols'
        )


def __restrictToTLDSetter( alias, param ):
    if isinstance( param, dict ):
        return\
            { 'restrictToTLDValidator_enabled':True
            , 'restrictToTLD_required': param
            }
    else:
        return\
            { 'restrictToTLDValidator_enabled': False
            }

Domain = Compose\
    ( CommonDomainPreValidaton().tag('prevalidation')
    & Split('.').tag('split')
    & Len(min=2).tag('numSubdomains')
    & ForEach\
        ( ~(Blank()).tag('format') & DomainLabel\
            ( prevalidation_enabled=False
            ).tag('domainLabel')
        )
    & Field( '.(-1)', In([]).tag('restrictToTLD') ).tag('restrictToTLDValidator')
    & Join('.')
    & ResolveDomain().tag('resolve',False)
    ).paramAlias\
        ( convertToString='string_convert'
        , updateValue='update_enabled'
        , eliminateWhiteSpace='eliminateWhiteSpace_enabled'
        , toLower='toLower_enabled'
        , restrictToTLD= __restrictToTLDSetter
    ).messageAlias\
        ( blank=('string_blank','toLower_blank')
        , missing='string_missing'
        , tooLong='domainLabel_tooLong'
        , type='string_type'
        , format = ('format_fail','numSubdomains_fail')
        , restrictToTLD= 'restrictToTLD_fail'
        , invalidSymbols='domainLabel_invalidSymbols'
    ).messages\
        ( blank="Please provide a value"
        , format='Invalid domain name format, try my.domain.com'
        , restrictToTLD= 'TLD not allowed. Allowed TLDs are %(required)s'
        , tooLong="A domain label cannot exceed %(max)i characters"
        )


EmailLocalPart = Compose\
    ( ( String.convert().tag('string')
    & EliminateWhiteSpace().tag('eliminateWhiteSpace') ).tag('prevalidation')
    & Encode('ascii').tag('validSymbols')
    & UpdateValue().tag('update')
    ).paramAlias\
        ( convertToString='string_convert'
        , updateValue='update_enabled'
        , eliminateWhiteSpace='eliminateWhiteSpace_enabled'
    ).messageAlias\
        ( blank=('string_blank','validSymbols_blank')
        , missing='string_missing'
        , type='string_type'
        , invalidSymbols='validSymbols_fail'
    ).messages\
        ( blank='Please enter a domain name'
        , invalidSymbols='Localpart contains invalid symbols'
        )

"""
class EmailSchema( Schema ):

    returnList = True

    pre_validate\
        ( String.convert().tag('string')
        , EliminateWhiteSpace().tag('eliminateWhiteSpace')
        , UpdateValue().tag('update')
        , Split('@',1).tag('split')
        )

    fieldset\
        ( 'localPart'
            , (~Blank()).tag('format')
            & EmailLocalPart( prevalidation_enabled=False ).tag('localPart')
        , 'domainPart'
            , Lower() & (~Blank()).tag('format')
            & Domain( prevalidation_enabled=False ).tag('domainPart')
        )

    post_validate\
        ( Join('@')
        )

Email = Compose\
        ( EmailSchema()
        ).paramAlias\
            ( eliminateWhiteSpace = 'eliminateWhiteSpace_enabled'
            , updateValue = 'update_enabled'
        ).messageAlias\
            ( blank = ('string_blank','split_blank' )
            , missing = 'string_missing'
        ).messages\
            ( blank = 'Please enter an email address'
            , format_fail = 'Invalid email format ( try my.email@address.com )'
            , localPart_invalidSymbols = u"The part before @ (%(value)s) contains invalid symbols"
            , domainPart_restrictTLD="Invalid top level domain %(value)s, allowed TLD are %(required)"
            , domainPart_tooLong="Domain part %(value)s is too long (max %(max)s characters)"
            , domainPart_format="Invalid domain name format (%(value)s)"
            , domainPart_invalidSymbols="Domain part %(value)s contains invalid characters"
            )

"""

class NestedPostConverter( ValidatorBase ):

    def validate( self, context, value ):
        resultset = {}

        for (key, val) in value.iteritems():
            parts = key.split('.')

            result = resultset

            while len(parts)>1:
                part = parts.pop(0)
                if part not in result:
                    if not part in result:
                        result[part] = {}
                result = result[part]
 
            result[parts[0]] = val

        return resultset


NestedPost = Compose\
    ( Dict().tag('type')
    & NestedPostConverter()
    ).messageAlias\
        ( type='type_fail'
        )
