from require.basic import Integer, String

IntOrStr = Tagger(Integer().tag('integer') | String())

val = IntOrStr( integer_convert=True )


