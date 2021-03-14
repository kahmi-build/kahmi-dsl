
import ast
import astor
import textwrap
import typing as t

import pytest

from kahmi.dsl.parser.parser import KahmiParser, Token


def mkparser(text: str) -> KahmiParser:
  parser = KahmiParser(text, '<string>')
  if parser.tokenizer.current.tv == (Token.Indent, ''):
    parser.tokenizer.next()
  return parser


def ast_cmp(a: t.Union[ast.AST, t.Collection[ast.AST]], b: t.Union[ast.AST, t.Collection[ast.AST]]) -> None:
  if not isinstance(a, t.Collection):
    a = [a]
  if not isinstance(b, t.Collection):
    b = [b]
  def _to_source(node):
    if node is None:
      return '<<NONE>>\n'
    return astor.to_source(node)
  assert ''.join(map(_to_source, a)) == ''.join(map(_to_source, b))


def test_parse_stmt_line():
  ast_cmp(mkparser('abc; foo')._parse_stmt_line(-1), ast.parse('abc; foo').body)
  ast_cmp(mkparser('abc\nfoo')._parse_stmt_line(-1), ast.parse('abc').body)
  ast_cmp(mkparser('abc;\nfoo')._parse_stmt_line(-1), ast.parse('abc').body)


def test_parse_stmt_block():
  ast_cmp(mkparser('\nabc; foo')._parse_stmt_block(-1), ast.parse('abc; foo').body)
  ast_cmp(mkparser('\nabc\nfoo')._parse_stmt_block(-1), ast.parse('abc; foo').body)
  ast_cmp(mkparser('\nabc;\nfoo')._parse_stmt_block(-1), ast.parse('abc; foo').body)
  ast_cmp(mkparser('\n  abc;\n  foo')._parse_stmt_block(0), ast.parse('abc; foo').body)
  ast_cmp(mkparser('\n  abc = 42;\n  foo')._parse_stmt_block(0), ast.parse('abc = 42; foo').body)
  with pytest.raises(IndentationError):
    mkparser('\n  abc;\n    foo')._parse_stmt_block(0)
  # De-indent outside a closure allowed.
  ast_cmp(mkparser('\n  abc;\nfoo')._parse_stmt_block(0), ast.parse('abc').body)


def test_parse_closure_body():
  ast_cmp(mkparser('{ abc }')._parse_closure_body(), ast.parse('abc').body)
  ast_cmp(mkparser('{ abc = 42 }')._parse_closure_body(), ast.parse('abc = 42').body)
  ast_cmp(mkparser('{ abc = 42; foo }')._parse_closure_body(), ast.parse('abc = 42; foo').body)
  ast_cmp(mkparser('{\n  abc = 42;\n  foo }')._parse_closure_body(), ast.parse('abc = 42; foo').body)
  ast_cmp(mkparser('{\n  abc = 42;\n  foo }')._parse_closure_body(), ast.parse('abc = 42; foo').body)
  with pytest.raises(IndentationError):
    mkparser('{\n  abc = 42;\n   foo }')._parse_closure_body()
  # De-indent inside a closure not allowed.
  with pytest.raises(IndentationError):
    mkparser('{\n  abc = 42;\nfoo }')._parse_closure_body()

  ast_cmp(mkparser('''{
      abc = 42
      if abc == 99:
        print("hello!")
      elif True:
        pass
      else:
        pass
    }''')._parse_closure_body(),
    ast.parse(textwrap.dedent('''
      abc = 42
      if abc == 99:
        print("hello!")
      elif True:
        pass
      else:
        pass
    ''')))


def test_parse_closure_header():
  assert mkparser('() ->')._parse_closure_header() == []
  assert mkparser('(arg1) ->')._parse_closure_header() == ['arg1']
  assert mkparser('(arg1 # A comment! \n, arg2) ->')._parse_closure_header() == ['arg1', 'arg2']
  assert mkparser('arg ->')._parse_closure_header() == ['arg']
  assert mkparser('arg')._parse_closure_header() == None
  assert mkparser('()')._parse_closure_header() == None


def test_parse_closure_arglist():
  assert mkparser('()')._parse_closure_arglist() == []
  assert mkparser('(arg1)')._parse_closure_arglist() == ['arg1']
  assert mkparser('(arg1,)')._parse_closure_arglist() == ['arg1']
  assert mkparser('(arg1, # A comment! \n arg2, arg3)')._parse_closure_arglist() == ['arg1', 'arg2', 'arg3']
  assert mkparser('arg1')._parse_closure_arglist() == None
