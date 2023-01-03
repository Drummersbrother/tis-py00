import re
from collections import namedtuple

# Take from https://github.com/jhgorrell/tis-100-programs for testing

TokenDef = namedtuple("TokenDef", ("name", "matcher", "source_sink", "converter"))

# The tokens we're going to have
class TokenType(object):
    # The token definitions
    # (NAME, MATCHER, (SOURCE, SINK), CONVERTER)
    _defs = [
        # Instructions
        TokenDef("INSTRUCTION", "mov", (False, False), lambda s: "mov"),
        TokenDef("INSTRUCTION", "nop", (False, False), lambda s: "nop"),
        TokenDef("INSTRUCTION", "swp", (False, False), lambda s: "swp"),
        TokenDef("INSTRUCTION", "swt", (False, False), lambda s: "swt"),
        TokenDef("INSTRUCTION", "sav", (False, False), lambda s: "sav"),
        TokenDef("INSTRUCTION", "add", (False, False), lambda s: "add"),
        TokenDef("INSTRUCTION", "sub", (False, False), lambda s: "sub"),
        TokenDef("INSTRUCTION", "neg", (False, False), lambda s: "neg"),
        TokenDef("INSTRUCTION", "jmp", (False, False), lambda s: "jmp"),
        TokenDef("INSTRUCTION", "jez", (False, False), lambda s: "jez"),
        TokenDef("INSTRUCTION", "jnz", (False, False), lambda s: "jnz"),
        TokenDef("INSTRUCTION", "jgz", (False, False), lambda s: "jgz"),
        TokenDef("INSTRUCTION", "jlz", (False, False), lambda s: "jlz"),
        TokenDef("INSTRUCTION", "jro", (False, False), lambda s: "jro"),
        TokenDef("INSTRUCTION", "hcf", (False, False), lambda s: "hcf"),

        # Registers
        TokenDef("REGISTER", "acc", (True, True), lambda s: "ACC"),

        # Values
        TokenDef("INTEGER", re.compile(r"(-?([1-9])([0-9]*))|(0)"), (True, False), int),

        # Ports
        TokenDef("PORT", "up", (True, True), lambda s: "UP"),
        TokenDef("PORT", "down", (True, True), lambda s: "DOWN"),
        TokenDef("PORT", "left", (True, True), lambda s: "LEFT"),
        TokenDef("PORT", "right", (True, True), lambda s: "RIGHT"),
        TokenDef("PORT", "last", (True, True), lambda s: "LAST"),
        TokenDef("PORT", "any", (True, True), lambda s: "ANY"),
        TokenDef("PORT", "nil", (True, True), lambda s: "NIL"),

        # Whitespace and the like
        TokenDef("NODE_SPECIFIER", re.compile(r"(@)([0-9]+)"), (False, False), lambda s: int(s[1:])),
        TokenDef("SEPARATOR", re.compile(r",+"), (False, False), None),
        TokenDef("LABEL", re.compile(r"^(([0-9]|[a-zA-z]|[~`$%^&*()_\-+={}\[\]|\\;'\"<>.?/])+?:)"), (False, False), lambda s: s[:-1]),
        # A label inside an instruction, a label reference.
        # This has to stay in this position in the def list, since we want matches to not chose this is ports are available
        TokenDef("LABEL_REF", re.compile(r"([0-9a-zA-z~`$%^&*()_\-+={}\[\]|\\;'\"<>.?/])+"), (False, False),
                 lambda s: s),
        TokenDef("WHITESPACE", re.compile(r"[ \n\t]+"), (False, False), None),
        TokenDef("COMMENT", re.compile(r"#[ 0-9a-zA-z~`$%^&*()_\-+={}\[\]|\\;'\"<>.?/]+"), (False, False), None)
    ]

    _multi_defs = {}

# We set the def names to be attributes of the tokentype class
# If we get a name collision, we add those names into a list with the same name
for token in TokenType._defs:
    try:
        type_ = getattr(TokenType, token.name)

        # We check if there is already a list
        if token.name not in TokenType._multi_defs:
            TokenType._multi_defs[token.name] = [type_, token]
        else:
            TokenType._multi_defs[token.name].append(token)

    except AttributeError:
        # We add the name
        setattr(TokenType, token.name, token)

# We replace the single definitions in the tokentype class with _multi_defs
for name, val in TokenType._multi_defs.items():
    # We replace the name
    setattr(TokenType, name, val)

# Represents a token in a source string with a specific start position, type, and value.
Token = namedtuple("Token", ("type", "value", "slice"))


def get_first_token(source: str, start: int=0):
    """Gets the longest matching token from the source starting at start."""

    # Text to match on
    match_text = source[start:]

    # The token to return and the text it came from
    token = None
    token_text = ""

    for token_type in TokenType._defs:
        # We unpack the definition of the token
        name, pattern, src_snk, converter = token_type

        if isinstance(pattern, str):
            # We match text
            if not match_text.lower().startswith(pattern):
                continue
            # It matched
            match_value = pattern

        else:
            # We regex match
            match = pattern.match(match_text)

            # Did it match?
            if not match:
                 continue

            # We get the matched text
            match_value = match.group(0)

        # We only want to keep the longest matches
        if len(token_text) > len(match_value):
            continue

        # Some tokens have higher priority then LABEL_REF
        if token_type == TokenType.LABEL_REF and (token is not None):
            if token.type in (*TokenType.INSTRUCTION, *TokenType.PORT, TokenType.REGISTER, TokenType.INTEGER):
                continue

        token_text = match_value
        # We convert into a token
        if converter is not None:
            match_value = converter(match_value)
        token = Token(token_type, match_value, slice(start, start + len(token_text)))

    # We return the best token, or None if None were found
    return token

def lex_gen(text):
    """Generates a list of tokens for a source text."""

    # The starting index
    start = 0

    while True:
        if start >= len(text):
            break

        token = get_first_token(text, start)

        # We check if a token was found
        if token is None:
            break

        yield token

        # We append it to the list, store the ending of it into the starting index of the next one
        start = token.slice.stop

def lex(text):
    tokens = list(lex_gen(text))

    if len(tokens) == 0:
        raise SyntaxError("Was not able to parse anything, please write valid code.")

    # We check that all chars were used
    if not (tokens[0].slice.start == 0 and tokens[-1].slice.stop == len(text)):
        raise SyntaxError("Was not able to fully parse the code, end of code is char {0}, while end of source is char {1}. Peek of code ending:\n{2}".format(tokens[-1].slice.stop, len(text), text[tokens[-1].slice.stop - 10: tokens[-1].slice.stop + 10]))

    return tokens