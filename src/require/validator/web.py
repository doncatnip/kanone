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


class Domain( String ):

    messages\
        ( noHyphen="Domain cannot contain a hyphen at pos 2-3"
        , tooLong="Domain part %(domainPart)s is too long"
        , noSubdomains="No subdomains allowed"
        , maxSubdomains="Maximum allowed subdomains: %(maxSubdomains)s"
        , minSubdomains="Invalid domain name format ( try my.domain.com )"
        , invalid="Domain part %(domainPart)s contains invalid characters"
        , resolve="Domain name could not be resolved"
        , restrictTLD="TLD %(tld)s is not allowed"
        )

    re_domain = re.compile ( r'^(xn--)?([a-z0-9]+([-a-z0-9]+)*)$' ,re.IGNORECASE )

    def __init__( self, resolve=False, restrictTLD=None, minSubdomains=1, maxSubdomains=None,  strip=True, lower=True, update=False, strict=False):
        if maxSubdomains==0:
            if restrictTLD is not None:
                raise SyntaxError("Can not restrict top level domains when not allowing any subdomains")
            if resolve:
                raise SyntaxError("Cant resolve a single domain name ( maxSubdomains is set to 0 )")

        String.__init__(self, strip=strip, lower=lower, update=update, strict=strict )
        if minSubdomains>maxSubdomains:
            minSubdomains = maxSubdomains

        self.minSubdomains = minSubdomains
        self.maxSubdomains = maxSubdomains
        self.resolve = resolve

    def on_value( self, context, value ):
        value = String.on_value( self, context, value)

        if self.strip:
            domain = [ part.strip() for part in value.split('.') ]

        if self.update:
            context['value'] = '.'.join(domain)

        if self.maxSubdomains is not None:
            if len(domain)>(self.maxSubdomains+1):
                if self.maxSubdomains == 0:
                    raise Invalid("noSubdomains")
                else:
                    raise self.invalid("maxSubdomains",maxSubdomains=self.maxSubdomains)

        if len(domain)<self.minSubdomains:
            raise self.invalid('minSubdomains')

        if self.restrictTLD is not None:
            if not domain[-1] in self.restrictTLD:
                raise self.invalid('restrictTLD', tld=domain[-1])

        punydomain=''

        for part in domain:

            next = None

            if part[2:4] == '--':
                if not part.startswith('xn'):
                    raise self.invalid('noHyphen')

                next = part

            if next is None:
                puny = part.encode('punycode')

                if not puny.endswith('-'):
                    next='xn--'+puny
                else:
                    next = part

            if len(next)>63:
                raise self.invalid('tooLong', domainPart=part)

            if not self.re_domain.match( next ):
                raise self.invalid('invalid', domainPart=part)

            if punydomain:
                punydomain += '.'

            punydomain += next

        if self.resolve and not resolve_domain( punydomain ):
            raise self.invalid('resolve')

        return punydomain

class Email( String ):

    messages\
        ( format="Invalid email format ( try my.email@address.com )"
        , invalid=u"The part before @ (%(localPart)s) contains invalid symbols"
        , domain_noHyphen="Domain cannot contain a hyphen at pos 2-3"
        , domain_tooLong="Domain part %(domainPart)s is too long"
        , domain_invalid="Domain part %(domainPart)s contains invalid characters"
        , domain_resolve="Domain name could not be resolved"
        , domain_restrictTLD="TLD %(tld)s is not allowed"
        )

    mail_re = r'([^@]+)@(.+))$'

    def __init__( self, restrictTLD=None, resolve=False, strip=True, lower=True, update=False, strict=False ):
        String.__init__(self, strip=strip, lower=lower, update=update, strict=strict )
        self.domainValidator = Domain\
            ( restrictTLD=restrictTLD
            , resolve=resolve
            , strip=strip
            , lower=lower
            , strict=strict
            , update=update
            )

    def on_value( self, context, value):
        value = String.on_value( self, context, value )

        mail = re.search(self.mail_re,value)

        if not mail or len(mail.groups()) != 2:
            raise self.invalid( 'format' )

        localPart = mail.group(1)
        if self.strip:
            localPart = localPart.strip()

        domainContext = self.domainValidator( mail.group(2) )
        if self.update:
            context['value'] = u"%s@%s" % (domainContext.value, localPart )

        try:
            localPart = localPart.encode('ascii')
        except UnicodeEncodeError,e:

        try:
            domain = domainContext.result
        except Invalid,e:
            raise self.invalid( 'domain_'+e.type.split('.')[-1], **e.extra )

        return ("%s@%s" % (localPart, domain))


DomainName = Tagger\
    ( String( lower=True, eliminateWhiteSpace=True

Domain = Tagger\
    ( String().alter( lower=True, eliminateWhiteSpace=True, update=True ).tag('input')
    & Split('.').tag('format')
    & Len().tag('numSubdomains')
    & ForEach\
        ( DomainNameValidator().tag('subdomain')
        , onLast=In().tag('restrictTLD')
        )
    & Join('.')
    & DomainLookup(enabled=False).tag('resolve')
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


EmailLocalPart = Tagger\
    ( String.( toLowerCase=True, eliminateWhiteSpace=True, updateValue=True ).tag('input')
    & EmailLocalPartValidator().tag('format')
    )


class EmailSchema( Schema ):

    returnList = True

    pre_valiate\
        ( String.convert().tag('string')
        , Lower().tag('lower')
        , EliminateWhiteSpace().tag('eliminateWhiteSpace')
        , Update().tag('updateInput')
        , Split('@',1).tag('format')
        )

    fieldset\
        ( 'localPart',  (~Blank()).tag('format') & EmailLocalPartValidator().tag('localPart')
        , 'domainPart', (~Blank()).tag('format') & Domain( input_enabled=False ).tag('domainPart')
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

