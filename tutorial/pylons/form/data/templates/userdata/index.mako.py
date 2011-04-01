# -*- encoding:utf-8 -*-
from mako import runtime, filters, cache
UNDEFINED = runtime.UNDEFINED
__M_dict_builtin = dict
__M_locals_builtin = locals
_magic_number = 5
_modified_time = 1301647046.273705
_template_filename='/home/boo/devel/require2/tutorial/pylons/form/form/templates/userdata/index.mako'
_template_uri='/userdata/index.mako'
_template_cache=cache.Cache(__name__, _modified_time)
_source_encoding='utf-8'
from webhelpers.html import escape
_exports = []


def render_body(context,**pageargs):
    context.caller_stack._push_frame()
    try:
        __M_locals = __M_dict_builtin(pageargs=pageargs)
        h = context.get('h', UNDEFINED)
        __M_writer = context.writer()
        # SOURCE LINE 1
        __M_writer(u'<a href="')
        __M_writer(escape(h.url(controller='userdata',action='edit')))
        __M_writer(u'">Edit user data</a>\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


