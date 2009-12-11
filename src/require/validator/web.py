import re, sys

from ..lib import pre_validate, missing, IGNORE, ValidationState, SchemaBase
from ..error import *

from .. import settings as s

from .simple import String, Dict
from .core import Validator

def domain2puny( domain ):
    retval=''

    for part in domain.split('.'):
        try:
            part.encode('ascii')
        except:
            try:
                part='xn--'+part.encode('punycode')
            except:
                return False

        retval += part

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

        domain = domain2puny( mail.group(2) )
        if domain == False:
            raise Invalid( self.msg[2], domain = mail.group(2) )

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
