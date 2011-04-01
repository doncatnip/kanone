import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect

from form.lib.base import BaseController, render

from require import *
from require.adapter.pylons import form

log = logging.getLogger(__name__)

class UserdataController(BaseController):

    def index(self):
        return render('/userdata/index.mako')

    @form\
        ( Schema \
            ( 'name', String()
            , 'email', web.Email(domainPart_restrictToTLD=['de','com'])
            )
        )
    def edit( self, context ):
        return render('/userdata/edit.mako', extra_vars={'form':context})

    @edit.init
    def edit( self, context ):
        context( 'name' ).value = 'bob'
        context( 'email' ).value = 'bob@some.domain'

    @edit.success
    def edit( self, result ):
        return render( '/userdata/edit_success.mako', extra_vars=result )
