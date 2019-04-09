from ..lib import Invalid

from .core import ValidatorBase, Validator, Compose, Tmp, Item, Call, If, messages
from .basic import String, Dict, Date, DateTime
from .alter import Encode, Decode, Lower, EliminateWhiteSpace, Split, Join, UpdateValue
from .check import Match, In, Len
from .schema import Schema, ForEach

from . import cache

import re
import warnings

@messages\
    ( fail='Domain offers no mailserver'
    )
class MXLookup( Validator ):
    def setArguments( self ):
        try:
            import dns.resolver
        except:
            warnings.warn('MX lookup disabled. Please install dnspython to enable dns lookups.', ImportWarning, stacklevel=2)
            self.on_value = self.resolveDisabled
        else:
            self.resolver = dns.resolver

    def resolveDisabled( self, context, value ):
        warnings.warn('MX lookup failed for domain %s. Please install dnspython to enable dns lookups.', RuntimeWarning, stacklevel=2)
        return value

    def on_value( self, context, value ):
        r = None
        try:
            r = self.resolver.query(value, 'MX')
        except self.resolver.NXDOMAIN:
            pass
        if not r:
            raise Invalid( value, self )

        return value


CommonDomainPreValidaton =\
    ( String.convert().tag('string')\
    & EliminateWhiteSpace().tag('eliminateWhiteSpace')\
    & Lower().tag('toLower')\
    & UpdateValue().tag('update')
    ).tag('prevalidation')

ComposedDomainLabel = Compose\
    ( CommonDomainPreValidaton
    & cache.Set('domainLabel')
    &   If  ( Match( re.compile(r'^xn--') )
            , Tmp( Encode('utf8') & Decode('idna').tag('decodeIdna') & cache.Set('domainLabelUnicode') )
            , cache.Set('domainLabelUnicode') & Encode('idna').tag('encodeIdna') & Decode('utf8')
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
        ( blank='Please provide a value'
        , tooLong='A domain label can have max %(max)i characters'
        , invalidSymbols='The domain name contains invalid symbols'
        )


def __restrictToTLDSetter( alias, param ):
    if isinstance( param, list ) or isinstance( param, tuple ) or isinstance( param, set ):
        return\
            { 'restrictToTLDValidator_enabled': True
            , 'restrictToTLD_criteria': param
            }
    else:
        return\
            { 'restrictToTLDValidator_enabled': False
            }

def __domain_save_nonidna( context, value ):
    domainName = context.cache.get('domainName',None)
    
    if domainName is None:
        domainName = ''
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
        , createContextChildren=False
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
        ( blank="Please provide a value"
        , format='Invalid domain name format, try my.domain.com'
        , restrictToTLD= 'TLD not allowed. Allowed TLDs are %(criteria)s'
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
        ( tooLong='Email local-part may only be up to %(max)i characters long'
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
        , createContextChildren=False
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
        , domainPart_restrictToTLD="Invalid top level domain %(domainLabel)s, allowed TLD are %(criteria)s"
        , domainPart_tooLong="Domain part is too long. Max %(max)s characters allowed per domain label"
        , domainPart_format="Invalid domain name format: %(domainPart)s"
        , domainPart_invalidSymbols="Domain part contains invalid characters: %(domainLabel)s"
        )


DateField = Compose\
    ( String.convert()
    & EliminateWhiteSpace()
    &   ( Date.convert( '%y-%m-%d' )
        | Date.convert( '%Y-%m-%d' )
        | Date.convert( '%d.%m.%y' )
        | Date.convert( '%d.%m.%Y' ).tag('dateConverter')
        )
    ).messageAlias\
        ( format='dateConverter_convert'
    ).messages\
        ( format='Invalid date format ( try YY(YY)-MM-DD or DD.MM.YY(YY) )'
        )
   
DateTimeField = Compose\
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
        ( format='Invalid date format ( try YY(YY)-MM-DD or DD.MM.YY(YY) )'
        )


class NestedPostConverter( ValidatorBase ):


    def validate( self, context, value ):
        resultset = {}

        for (key, val) in value.items():
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
