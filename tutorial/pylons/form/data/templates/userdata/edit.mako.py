# -*- encoding:utf-8 -*-
from mako import runtime, filters, cache
UNDEFINED = runtime.UNDEFINED
__M_dict_builtin = dict
__M_locals_builtin = locals
_magic_number = 5
_modified_time = 1301649657.547354
_template_filename='/home/boo/devel/require2/tutorial/pylons/form/form/templates/userdata/edit.mako'
_template_uri='/userdata/edit.mako'
_template_cache=cache.Cache(__name__, _modified_time)
_source_encoding='utf-8'
from webhelpers.html import escape
_exports = []


def render_body(context,**pageargs):
    context.caller_stack._push_frame()
    try:
        __M_locals = __M_dict_builtin(pageargs=pageargs)
        h = context.get('h', UNDEFINED)
        form = context.get('form', UNDEFINED)
        __M_writer = context.writer()
        # SOURCE LINE 1
        __M_writer(u'<form action="')
        __M_writer(escape(h.url(controller='userdata',action='edit')))
        __M_writer(u'" method="POST">\n    Name: <input type="text" name="name" value="')
        # SOURCE LINE 2
        __M_writer(escape(form('name').value))
        __M_writer(u'"/><br />\n    ')
        # SOURCE LINE 3
        __M_writer(escape(form('name').error))
        __M_writer(u'\n    Email: <input type="text" name="email" value="')
        # SOURCE LINE 4
        __M_writer(escape(form('email').value))
        __M_writer(u'"/><br />\n    ')
        # SOURCE LINE 5
        __M_writer(escape(form('email').error))
        __M_writer(u'\n    <input type="submit" value="Submit" />\n</form>\n')
        return ''
    finally:
        context.caller_stack._pop_frame()


