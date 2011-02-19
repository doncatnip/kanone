import re

from ..lib import messages

from .basic import String, Dict
from .alter import Lower, EliminateWhiteSpace, Split, Join, Update

def resolve_domain( domain ):

    import DNS

    a=DNS.DnsRequest(domain, qtype='mx').req().answers
    if not a:
        a=DNS.DnsRequest(domain, qtype='a').req().answers

    dnsdomains=[x['data'] for x in a]
    if not dnsdomains:
        return False
    return True

"""
class DomainLabelValidator( Validator ):

    messages\
        ( noHyphen="Domain cannot contain a hyphen at pos 2-3"
        , tooLong="Domain part is too long"
        , invalid="Domain part contains invalid characters"
        )

    re_domain = re.compile ( r'^(xn--)?([a-z0-9]+([-a-z0-9]+)*)$' ,re.IGNORECASE )

    def __init__( self, convertToPunicode=True ):
        self.convertToPunicode = convertToPunicode

    def on_value( self, context, value ):

        if value[2:4] == '--':
            if not value.startswith('xn'):
                raise self.invalid('noHyphen')

        else:
            puny = value.encode('punycode')

            if not puny.endswith('-'):
                punydomain='xn--'+puny
            else:
                punydomain=puny

        if len(punydomain)>63:
            raise Invalid('tooLong')

        if not self.re_domain.match( next ):
            raise Invalid('invalid')

        if self.convertToPunicode:
            return punydomain
        else:
            return value
"""
CommonDomainPreValidaton\
    = String.convert().tag('string')
    & EliminateWhiteSpace().tag('eliminateWhiteSpace')
    & Lower().tag('toLower')
    & Update().tag('update')
    & (~Blank()).tag('notBlank')

DomainLabel = Compose\
    ( CommonDomainPreValidaton().tag('prevalidation')
    & cache.Save(result='preEncode').tag('returnNonPuny')
    & ( Match(re'^xn--') | Encode('punycode') ).tag('punyCode')
    & (~Match(re'^??--')).tag('noHyphen')
    & Len(max=63).tag('tooLong')
    & (~Match(re'^[a-z0-9]+([-a-z0-9]+)*$')).tag('invalidSymbols')
    & cache.Restore(result='preEncode').tag('returnNonPuny')
    ).paramAlias\
        ( convertToString='string_convert'
        , convertToPunicode='punyCode_enabled'
        , updateValue='update_enabled'
        , eliminateWhiteSpace='eliminateWhiteSpace_enabled'
        , toLower='toLower_enabled'
        , returnNonPuny='returnNonPuny_enabled'
    ).messageAlias\
        ( type='string_type'
        , noHyphen='noHyphen_fail'
        , tooLong='tooLong_fail'
        , invalidSymbols='invalidSymbols_fail'
        , blank=("notBlank_fail","string_blank")
    )




Domain = Compose\
    ( commonDomainPreValidaton.tag('prevalidation')
    & Split(separator='.')
    & Len(min=2).tag('numSubdomains')
    & ForEach\
        ( DomainLabel\
            ( prevalidation_enabled=False
            ).tag('domainLabel')
        , onLast=In().tag('restrictTLD',False)
        )
    & Join('.')
    & DomainLookup().tag('resolve',False)
    )

EmailLocalPart = Tagger\
    ( String.( toLowerCase=True, eliminateWhiteSpace=True, updateValue=True ).tag('input')
    & EmailLocalPartValidator().tag('format')
    )


class EmailSchema( Schema ):

    returnList = True

    pre_valiate\
        ( String.convert().tag('string')
        , EliminateWhiteSpace().tag('eliminateWhiteSpace')
        , Update().tag('updateInput')
        , Split('@',1).tag('format')
        )

    fieldset\
        ( 'localPart',  (~Blank()).tag('format') & EmailLocalPart().tag('localPart')
        , 'domainPart', (~Blank()).tag('format') & Domain().tag('domainPart')
        )

    post_validate\
        ( Join('@')
        )

Email = Tagger( EmailSchema ).messages\
        ( blank = 'Please enter an email address'
        , format_fail = 'Invalid email format ( try my.email@address.com )'
        , localPart_invalid = u"The part before @ (%(value)s) contains invalid symbols"
        , domainPart_restrictTLD="Invalid top level domain %(tld)s"
        , domainPart_noHyphen="Domain cannot contain a hyphen at pos 2-3"
        , domainPart_tooLong="Domain part %(subdomain)s is too long"
        , domainPart_invalid="Domain part %(subdomain)s contains invalid characters"
        )



class EmailLocalPartValidator( Validator ):

    messages\
        ( invalid=u"Local part contains invalid symbols"
        )

    def on_value( self, context, value):
        try:
            localPart = localPart.encode('ascii')
        except UnicodeEncodeError,e:
            raise self.invalid( 'invalid' )
        return localPart




class NestedPost( Dict ):

    def on_value( self, context, value ):
        value = Dict.on_value( self, context, value )
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

