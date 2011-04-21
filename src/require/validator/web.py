import re

from ..lib import messages

from .core import ValidatorBase, Validator, Compose, Pass, Tmp, Item
from .basic import String, Dict, DateTime
from .alter import Encode, Lower, EliminateWhiteSpace, Split, Join, UpdateValue, Insert, Format,Strip
from .check import Match, Blank, In, Len
from .schema import Schema, ForEach, Field
from .debug import Print

from . import cache

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
            raise Invalid( value, self )

        return value


CommonDomainPreValidaton =\
    ( String.convert().tag('string')\
    & EliminateWhiteSpace().tag('eliminateWhiteSpace')\
    & Lower().tag('toLower')\
    & UpdateValue().tag('update')
    ).tag('prevalidation')

# We should propably implement a dedicated and therefore
# faster validator.
# ( nested And/Or with a few elements still slow things down )
ComposedDomainLabel = Compose\
    ( CommonDomainPreValidaton
    & cache.Set('domainLabel')
    &   ( Match( re.compile(r'^xn--') )
        |   ( Encode('punycode').tag('encodePuny')
            &   (   (   Match( re.compile(r'.*-$') )
                    &   cache.Get('domainLabel')
                    )
                |   Insert('xn--',0)
                )
            )
        ).tag('punycode')
    & Len(min=2, max=63).tag('length')
    & Match(re.compile(r'^(xn--)?[a-z0-9]+[\-a-z0-9]+$')).tag('validSymbols')
    & cache.Get('domainLabel').tag('returnNonPuny', False)
    ).paramAlias\
        ( convertToString='string_convert'
        , updateValue='update_enabled'
        , eliminateWhiteSpace='eliminateWhiteSpace_enabled'
        , toLower='toLower_enabled'
        , convertToPunycode='punycode_enabled'
        , returnNonPuny='returnNonPuny_enabled'
    ).messageAlias\
        ( type='string_type'
        , tooLong='length_max'
        , tooShort='length_min'
        , invalidSymbols='validSymbols_fail'
        , blank=("toLower_blank","string_blank","encodePuny_blank")
        , missing="string_missing"
    ).messages\
        ( blank='Please provide a value'
        , tooLong='A domain label can have max %(max)i characters'
        , tooShort='A domain label must have at least %(min)i characters'
        , invalidSymbols='The domain name contains invalid symbols'
        )


def __restrictToTLDSetter( alias, param ):
    if isinstance( param, list ) or isinstance( param, tuple ) or isinstance( param, set ):
        return\
            { 'restrictToTLDValidator_enabled':True
            , 'restrictToTLD_required': param
            }
    else:
        return\
            { 'restrictToTLDValidator_enabled': False
            }

Domain = Compose\
    ( CommonDomainPreValidaton
    & Split('.').tag('split')
    & Len(min=2).tag('numSubdomains')
    & ForEach\
        ( ComposedDomainLabel\
            ( prevalidation_enabled=False
            ).tag('domainLabel')
        , createContextChilds=False
        )
    & Item\
        ( -1
        , In([]).tag('restrictToTLD')
        , alter=False
        ).tag('restrictToTLDValidator', False)
    & Join('.')
    & ResolveDomain().tag('resolve',False)
    ).paramAlias\
        ( convertToString='string_convert'
        , convertToPunycode='domainLabel_convertToPunycode'
        , returnNonPuny='domainLabel_returnNonPuny'
        , updateValue='update_enabled'
        , eliminateWhiteSpace='eliminateWhiteSpace_enabled'
        , toLower='toLower_enabled'
        , restrictToTLD= __restrictToTLDSetter
    ).messageAlias\
        ( blank=('string_blank','toLower_blank')
        , missing='string_missing'
        , tooLong='domainLabel_tooLong'
        , type='string_type'
        , format = ('numSubdomains_min','domainLabel_blank')
        , restrictToTLD= 'restrictToTLD_fail'
        , invalidSymbols='domainLabel_invalidSymbols'
    ).messages\
        ( blank="Please provide a value"
        , format='Invalid domain name format, try my.domain.com'
        , restrictToTLD= 'TLD not allowed. Allowed TLDs are %(required)s'
        , tooLong="A domain label cannot exceed %(max)i characters"
        )


EmailLocalPart = Compose\
    (   ( String.convert().tag('string')
        & EliminateWhiteSpace().tag('eliminateWhiteSpace')
        & UpdateValue().tag('update')
        ).tag('prevalidation')
    & Len(max=64).tag('length')
    & Match(re.compile(r'^[a-z0-9!#$%&\'\*\+\-\/\=\?\^_`\{\|\}~]+(\.[a-z0-9!#$%&\'\*\+\-\/\=\?\^_`\{\|\}~]+)*$', re.I)).tag('validSymbols')
    ).paramAlias\
        ( convertToString='string_convert'
        , updateValue='update_enabled'
        , eliminateWhiteSpace='eliminateWhiteSpace_enabled'
    ).messageAlias\
        ( blank=('string_blank','validSymbols_blank','length_blank')
        , missing='string_missing'
        , tooLong='length_max'
        , type='string_type'
        , invalidSymbols='validSymbols_fail'
    ).messages\
        ( tooLong='Email local-part only may be up do %(max)i characters long'
        , invalidSymbols='Localpart contains invalid symbols'
        )


Email = Compose\
    ( String.convert().tag('string')
    & EliminateWhiteSpace().tag('eliminateWhiteSpace')
    & Split('@',1).tag('split')
    & Tmp\
        ( Item( 1 , Lower().tag('doLowerDomainPart') ).tag('itemDomainPart')
        & Join('@' )
        & UpdateValue().tag('update')
        ).tag('lowerDomainPart')
    & Schema\
        ( 'localPart'
            ,  cache.Set('localPart') & EmailLocalPart( prevalidation_enabled=False ).tag('localPart')
        , 'domainPart'
            ,  cache.Set('domainPart') & Domain( prevalidation_enabled=False ).tag('domainPart')
        , createContextChilds=False
        , returnList=True
        )
    & Join('@')
    ).paramAlias\
        ( eliminateWhiteSpace = 'eliminateWhiteSpace_enabled'
        , updateValue = 'update_enabled'
        , lowerDomainPart = 'lowerDomainPart_enabled'
    ).messageAlias\
        ( blank = ('string_blank','split_blank' )
        , missing = 'string_missing'
        , format = \
            ( 'itemDomainPart_blank'
            , 'itemDomainPart_notFound'
            , 'doLowerDomainPart_blank'
            , 'localPart_blank'
            , 'domainPart_blank'
            )
    ).messages\
        ( blank = 'Please enter an email address'
        , format = 'Invalid email format ( try my.email@address.com )'
        , localPart_invalidSymbols = "The part before @ (%(localPart)s) contains invalid symbols"
        , domainPart_restrictToTLD="Invalid top level domain %(domainLabel)s, allowed TLD are %(required)s"
        , domainPart_tooLong="Domain part %(domainLabel)s is too long (max %(max)s characters)"
        , domainPart_format="Invalid domain name format (%(domainPart)s)"
        , domainPart_invalidSymbols="Domain part %(domainLabel)s contains invalid characters"
        )


"""
def defaultMonthByNameGetter( context, monthName ):


DateSchema = Compose\
    ( Schema\
        ( 'year'
            , If( String(), EliminateWhiteSpace() )
            & Integer.convert()
            & ( Len(min=4 max=4 ) | Len( min=2, max=2 ) )
        , 'month'
            , If\
                ( String()
                , EliminateWhiteSpace()
                    & Lower()
                    & Call( defaultMonthNameGetter ).tag('monthNameGetter')
                )
            & Integer.convert()
            & Len( min=1, max=2 )
            
        , 'day'
            , If( String(), EliminateWhiteSpace() )
            & Integer.convert()
            & Len( min=1, max=2 )
        )
    )
    
DateField = Compose\
    ( String.convert()
    & Strip()
    & cache.Set('value')
    & cache.Get('formats',[]).tag('getFormats')
    & ForEach\
        ( cache.Set('currentFormat')
        & cache.Get('value')
        , createContextChilds=False
        , until=Extract( cache.Get('currentFormat') )
        ).tag('extract')
    & DateSchema( createContextChilds=False ).tag('dateSchema')
    & Format( '%(Y)s-%(m)s-%(d)s', **{'Y':Item('year'),'m':Item('month'),'d':Item('day')} )
    &   ( DateTime.convert( '%Y-%m-%d' )
        | DateTime.convert( '%y-%m-%d' ).tag('DateTimeConverter')
        )
    & Tmp ( If( cache.Has('minDate'), ( cache.Get('minDate') > CurrentValue() ).tag('checkMinDate') ) )
    & Tmp ( If( cache.Has('maxDate'), ( cache.Get('maxDate') < CurrentValue() ).tag('checkMaxDate') ) )
    ).paramAlias\
        ( formats='getFormats_default'
    ).messageAlias\
        ( monthName='monthNameGetter_fail'
        )

DateField = DateField(
    formats =\
        [ re.compile(r'^(?P<Y>([0-9]{2}|[0-9]{4})\-(?P<m>([0-9]+|[^0-9\-]+))\-(?P<d>[0-9]+)$')
        , re.compile(r'^(?P<Y>[0-9]{2,4})\-(?P<m>([0-9]+|[^0-9\-]+))\-(?P<d>[0-9]+)$')
        , re.compile(r'^(?P<Y>[0-9]{2,4})\-(?P<m>([0-9]+|[^0-9\-]+))\-(?P<d>[0-9]+)$')
        ]
"""


class NestedPostConverter( ValidatorBase ):

    def validate( self, context, value ):
        resultset = {}

        for (key, val) in value.iteritems():
            parts = key.split('.')

            result = resultset

            while len(parts)>1:
                part = parts.pop(0)
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
