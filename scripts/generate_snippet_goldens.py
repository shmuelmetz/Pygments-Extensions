#!/usr/bin/env python3
"""Generate Pygments-format golden-file lexer tests.

Replicates the exact token-formatting algorithm from Pygments' own
tests/conftest.py (PytestGoldenTestItem._prettyprint_tokens), verified
directly against pygments/pygments@master 2026-09-01, so files written
by this script are byte-for-byte what `tox -- --update-goldens` would
produce once this lexer lives inside an actual pygments/pygments
checkout. This project's lexer isn't registered with Pygments' own
lexer lookup (get_lexer_by_name), so this script imports the lexer
class directly instead of going through that lookup -- the only
difference from upstream's own generator, and irrelevant to the
output format itself.

Usage:
    python scripts/generate_snippet_goldens.py \
        --lexer pygments_extensions.lexers.oorexx.OORexxLexer \
        tests/snippets/oorexx/test_something.txt

Each target file must already exist and contain the source snippet as
its entire content (no --input--/--tokens-- markers yet) -- the
script reads that as the input, tokenizes it, and rewrites the file
with the full --input--/--tokens-- golden format. Review the output
before committing, per Pygments' own contributing guidelines.
"""

import argparse
import importlib
import sys

from pygments.token import Error


def prettyprint_tokens(tokens, allow_errors=False):
    for tok, val in tokens:
        if tok is Error and not allow_errors:
            raise ValueError(f'generated Error token at {val!r}')
        yield f'{val!r:<13} {str(tok)[6:]}'
        if val.endswith('\n'):
            yield ''


def load_lexer_class(dotted_path):
    module_path, _, class_name = dotted_path.rpartition('.')
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lexer', required=True,
                         help='dotted path to the lexer class, e.g. '
                              'pygments_extensions.lexers.oorexx.OORexxLexer')
    parser.add_argument('--allow-errors', action='store_true',
                         help='do not fail on Error tokens (for negative-'
                              'case snippets where Error is expected)')
    parser.add_argument('files', nargs='+',
                         help='snippet file(s) to convert in place')
    args = parser.parse_args()

    lexer_class = load_lexer_class(args.lexer)
    lexer = lexer_class()

    for path in args.files:
        with open(path, encoding='utf-8') as f:
            content = f.read()

        if content.startswith('---input---'):
            print(f'{path}: already in golden format, extracting input section', file=sys.stderr)
            input_text = content.split('---input---\n', 1)[1].split('\n---tokens---')[0]
        else:
            input_text = content

        tokens = list(lexer.get_tokens(input_text))
        actual = '\n'.join(prettyprint_tokens(tokens, args.allow_errors)).rstrip('\n') + '\n'

        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('---input---\n')
            f.write(input_text)
            if not input_text.endswith('\n'):
                f.write('\n')
            f.write('\n---tokens---\n')
            f.write(actual)

        print(f'wrote {path}')


if __name__ == '__main__':
    main()
