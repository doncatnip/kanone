import re, sys

from ..lib import pre_validate, missing, IGNORE, ValidationState, SchemaBase
from ..error import *

from .. import settings as s

from .simple import String, Dict
from .core import Validator

re_domain = re.compile ( r'^(xn--)?([a-z0-9]+([-a-z0-9]+)*)$' )

class DomainInvalid(Exception):
    def __init__(self, msg, part):
        self.part = part
        Exception.__init__(self, msg)

    def __str__(self ):
        return self[0] % self.part

    __repr__ = __str__

class DomainInvalidCharacter( DomainInvalid ):
    pass

class DomainInvalidFormat( DomainInvalid ):
    pass

class DomainTooLong( DomainInvalid ):
    pass

def domain2puny( domain ):
    retval=''

    for part in domain.split('.'):
        if part[2:4] == '--':
            raise DomainInvalidFormat("Domain cannot contain a hyphen at pos 2-3", part=part)

        puny = part.encode('punycode')

        if not puny.endswith('-'):
            next='xn--'+puny
        else:
            next = part

        if len(next)>63:
            raise DomainTooLong("Domain part %s is too long", part=part)
        if not re_domain.match( next ):
            raise DomainInvalidCharacter("Domain part %s contains invalid characters", part=part)

        retval += next

    return retval

def resolve_domain( domain ):

    import DNS

    a=DNS.DnsRequest(domain, qtype='mx').req().answers
    if not a:
        a=DNS.DnsRequest(domain, qtype='a').req().answers

    dnsdomains=[x['data'] for x in a]
    if not dnsdomains:
        return False
    return True


class Domain( Validator ):
    info = s.text.Domain.info
    msg = s.text.Domain.msg

    re_domain_tld = r'^(.+)\.([\w]{2,})$'

    pre_validate\
        ( String()
        )


    def __init__( self, no_tld = False, subdomain_max=None ):
        self.__no_tld__         = no_tld
        self.__subdomain_max__   = subdomain_max

    def on_value( self, context, value ):
        if not self.__no_tld__:
            domain = self.re_domain_tld.match( value )
            if not domain or len(domain.groups())<2:
                raise Invalid( self.msg[0] )

            domain, tld = domain.groups()
        else:
            domain = value

        if self.__subdomain_max__ is not None:
            if domain.count('.')>(self.__subdomain_max__+int(not self.__no_tld__)):
                if self.__subdomain_max__ == 0:
                    raise Invalid( self.msg[1] )
                else:
                    raise Invalid( self.msg[2], subdomain_max= self.__subdomain_max__ )

        try:
            domain = domain2puny( domain )
        except DomainInvalid,e:
            raise Invalid( e[0], part = e.part )

        if not self.__no_tld__:
            domain = "%s.%s" % (domain, tld)

        return domain

class Email( Validator ):

    info = s.text.Email.info
    msg = s.text.Email.msg

    pre_validate\
        ( String()
        )

    mail_re = r'([^@]+)@(.+)\.([\w]{2,})$'

    __resolve_domain__ = False

    def __extra__( self, context):
        return { 'resolve_domain': self.__resolve_domain__ }

    def __info__( self, context ):
        if self.__resolve_domain__:
            return self.info[1]
        else:
            return self.info[0]

    def on_value( self, context, value):
        value = value.strip()
        mail = re.search(self.mail_re,value)

        if not mail or len(mail.groups()) != 3:
            raise Invalid( self.msg[0] )

        try:
            domain = domain2puny( mail.group(2) )
        except DomainInvalid,e:
            raise Invalid( self.msg[2], domain = mail.group(2), part = e.part )

        localpart = mail.group(1)
        try:
            localpart.encode('ascii')
        except UnicodeEncodeError,e:
            raise Invalid( self.msg[1], localpart=localpart )

        domain=("%s.%s" % (domain, mail.group(3))).encode('ascii')

        if self.__resolve_domain__:
            if not resolve_domain( domain ):
                raise Invalid( self.msg[3], domain=domain )

        return ("%s@%s" % (localpart, domain)).encode('ascii')

    def resolve( self ):
        self.__resolve_domain__ = True
        return self


class NestedPost( Validator ):

    pre_validate\
        ( Dict()
        )

    def on_value( self, context, values ):
        resultset = {}

        for (key, value) in values.iteritems():
            parts = key.split('.')

            result = resultset

            while len(parts)>1:
                part = parts.pop(0)
                if part not in result:
                    if not part in result:
                        result[part] = {}
                result = result[part]
 
            result[parts[0]] = value

        return resultset
