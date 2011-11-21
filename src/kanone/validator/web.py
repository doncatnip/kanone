import re

from ..lib import messages, Invalid

from .core import ValidatorBase, Validator, Compose, Pass, Tmp, Item, Call, If
from .basic import String, Dict, DateTime
from .alter import Encode, Decode, Lower, EliminateWhiteSpace, Split, Join, UpdateValue, Insert, Format,Strip
from .check import Match, Blank, In, Len
from .schema import Schema, ForEach, Field
from .debug import Print

from . import cache

class MXLookup( Validator ):

    messages\
        ( fail='Domain offers no mailserver'
        )

    def on_value( self, context, value ):
        import DNS

        if not DNS.mxlookup(value):
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
    &   If  ( Match( re.compile(r'^xn--') )
            , Tmp( Decode('idna').tag('decodeIdna') & cache.Set('domainLabelUnicode') )
            , cache.Set('domainLabelUnicode') & Encode('idna').tag('encodeIdna')
            ).tag('idna')
    & cache.Set('domainLabel')
    & Len(max=63).tag('length')
    & Match(re.compile(r'^((([a-z][0-9])|([0-9][a-z])|([a-z0-9][a-z0-9\-]{1,2}[a-z0-9])|([a-z0-9][a-z0-9\-](([a-z0-9\-][a-z0-9])|([a-z0-9][a-z0-9\-]))[a-z0-9\-]*[a-z0-9]))|([a-z0-9]{1,2})|(xn\-\-[\-a-z0-9]*[a-z0-9]))$')).tag('validSymbols')
    #& create.List( cache.Get('domainLabel'), cache.Get('domainLabelUnicode') )
    & cache.Get('domainLabelUnicode').tag('returnUnicode')
    ).paramAlias\
        ( convertToString='string_convert'
        , updateValue='update_enabled'
        , eliminateWhiteSpace='eliminateWhiteSpace_enabled'
        , toLower='toLower_enabled'
        , extractIdna='idna_enabled'
        , returnUnicode='returnUnicode_enabled'
    ).messageAlias\
        ( type='string_type'
        , tooLong='length_max'
        , invalidSymbols=('validSymbols_fail','encodeIdna_fail','decodeIdna_fail')
        , blank=
            ("toLower_blank"
            ,"string_blank"
            ,"encodeIdna_blank"
            ,"decodeIdna_blank"
            ,"length_blank"
            )
        , missing="string_missing"
    ).messages\
        ( blank=u'Please provide a value'
        , tooLong=u'A domain label can have max %(max)i characters'
        , invalidSymbols=u'The domain name contains invalid symbols'
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

def __domain_save_nonidna( context, value ):
    domainName = context.cache.get('domainName',None)
    if domainName is None:
        context.cache['domainName'] = domainName = ''
    else:
        domainName += '.'

    domainName += context.cache.get('domainLabel')
    context.cache['domainName'] = domainName
    return value

Domain = Compose\
    ( CommonDomainPreValidaton
    & Split('.').tag('split')
    & Len(min=2).tag('numSubdomains')
    & ForEach\
        ( ComposedDomainLabel\
            ( prevalidation_enabled=False
            ).tag('domainLabel') & Call(__domain_save_nonidna)
        , createContextChilds=False
        )
    & Item\
        ( -1
        , In([]).tag('restrictToTLD')
        , alter=False
        ).tag('restrictToTLDValidator', False)
    & Join('.')\
    & Tmp( cache.Get('domainName') & MXLookup().tag('mxLookup') ).tag('resolve',False)\
    ).paramAlias\
        ( convertToString='string_convert'
        , extractIdna='domainLabel_extractIdna'
        , returnUnicode='domainLabel_returnUnicode'
        , updateValue='update_enabled'
        , eliminateWhiteSpace='eliminateWhiteSpace_enabled'
        , toLower='toLower_enabled'
        , resolve='resolve_enabled'
        , restrictToTLD= __restrictToTLDSetter
    ).messageAlias\
        ( blank=('string_blank','toLower_blank')
        , missing='string_missing'
        , tooLong='domainLabel_tooLong'
        , type='string_type'
        , format = ('numSubdomains_min','domainLabel_blank')
        , restrictToTLD= 'restrictToTLD_fail'
        , invalidSymbols='domainLabel_invalidSymbols'
        , resolve='mxLookup_fail'
    ).messages\
        ( blank=u"Please provide a value"
        , format=u'Invalid domain name format, try my.domain.com'
        , restrictToTLD= u'TLD not allowed. Allowed TLDs are %(required)s'
        , tooLong=u"A domain label cannot exceed %(max)i characters"
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
        ( tooLong=u'Email local-part only may be up do %(max)i characters long'
        , invalidSymbols=u'Localpart contains invalid symbols'
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
        ( blank = u'Please enter an email address'
        , format = u'Invalid email format ( try my.email@address.com )'
        , localPart_invalidSymbols = u"The part before @ (%(localPart)s) contains invalid symbols"
        , domainPart_restrictToTLD=u"Invalid top level domain %(domainLabel)s, allowed TLD are %(required)s"
        , domainPart_tooLong=u"Domain part %(domainLabel)s is too long (max %(max)s characters)"
        , domainPart_format=u"Invalid domain name format (%(domainPart)s)"
        , domainPart_invalidSymbols=u"Domain part %(domainLabel)s contains invalid characters"
        )


    
DateField = Compose\
    ( String.convert()
    & EliminateWhiteSpace()
    &   ( DateTime.convert( '%y-%m-%d' )
        | DateTime.convert( '%Y-%m-%d' )
        | DateTime.convert( '%d.%m.%y' )
        | DateTime.convert( '%d.%m.%Y' ).tag('dateTimeConverter')
        )
    ).messageAlias\
        ( format='dateTimeConverter_convert'
    ).messages\
        ( format=u'Invalid date format ( try YY(YY)-MM-DD or DD.MM.YY(YY) )'
        )


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