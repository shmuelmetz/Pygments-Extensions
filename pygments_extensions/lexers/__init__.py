"""Lexer modules for pygments-extensions.

Each lexer is registered with Pygments via the ``pygments.lexers`` entry
point group in pyproject.toml, not by importing it here -- Pygments
discovers third-party lexers through entry points, so this package does
not need to (and should not) eagerly import every lexer module itself.
"""
