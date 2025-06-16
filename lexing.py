# --- 1. Lexer ---
from enum import Enum
from json import dumps


class TokenType(Enum):
    # Keywords
    LET = "LET"
    FREE = "FREE"
    DEF = "DEF"
    STRUCT = "STRUCT"
    IF = "IF"
    ELSE = "ELSE"
    ELIF = "ELIF"
    WHILE = "WHILE"
    FOR = "FOR"
    RETURN = "RETURN"
    ENUM = "ENUM"
    RESULT = "RESULT"
    OK = "OK"
    ERR = "ERR"
    SPAWN = "SPAWN"
    IMPORT = "IMPORT"
    TRY = "TRY"
    CATCH = "CATCH"
    # Data Types
    INT8 = "INT8"
    INT16 = "INT16"
    INT32 = "INT32"
    INT64 = "INT64"
    UINT8 = "UINT8"
    UINT16 = "UINT16"
    UINT32 = "UINT32"
    UINT64 = "UINT64"
    FLOAT32 = "FLOAT32"
    FLOAT64 = "FLOAT64"
    CHAR = "CHAR"
    NULL = "NULL"
    STRING = "STRING"
    ARRAY = "ARRAY"
    # Operators
    ASSIGN = "ASSIGN"  # =
    PLUS = "PLUS"  # +
    MINUS = "MINUS"  # -
    MULTIPLY = "MULTIPLY"  # *
    DIVIDE = "DIVIDE"  # /
    MODULO = "MODULO"  # %
    EQUAL = "EQUAL"  # ==
    NOT_EQUAL = "NOT_EQUAL"  # !=
    GREATER_THAN = "GREATER_THAN"  # >
    LESS_THAN = "LESS_THAN"  # <
    GREATER_EQUAL = "GREATER_EQUAL"  # >=
    LESS_EQUAL = "LESS_EQUAL"  # <=
    AND = "AND"  # &
    OR = "OR"  # |
    XOR = "XOR"  # ^
    LSHIFT = "LSHIFT"  # <<
    RSHIFT = "RSHIFT"  # >>
    BIT_NOT = "BIT_NOT"  # ~
    POINTER_REF = "POINTER_REF"  # &
    POINTER_DEREF = "POINTER_DEREF"  # *
    DOT = "DOT"  # .
    # Brackets
    LPAREN = "LPAREN"  # (
    RPAREN = "RPAREN"  # )
    LBRACE = "LBRACE"  # {
    RBRACE = "RBRACE"  # }
    LBRACKET = "LBRACKET"  # [
    RBRACKET = "RBRACKET"  # ]
    SEMICOLON = "SEMICOLON"  # ;
    COLON = "COLON"  # :
    COMMA = "COMMA"  # ,
    # Literals
    INT_LITERAL = "INT_LITERAL"
    FLOAT_LITERAL = "FLOAT_LITERAL"
    CHAR_LITERAL = "CHAR_LITERAL"
    IDENTIFIER = "IDENTIFIER"
    STRING_LITERAL = "STRING_LITERAL"  # For future use? print("string")
    # Other
    EOF = "EOF"
    ARROW = "ARROW"


class Token:
    def __init__(self, token_type, value, line, column):
        self.type = token_type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f'<Token {self.type}: {self.value} at {self.line}:{self.column}>'


DATA_TYPES = {
    "int8": TokenType.INT8, "int16": TokenType.INT16, "int32": TokenType.INT32, "int64": TokenType.INT64,
    "uint8": TokenType.UINT8, "uint16": TokenType.UINT16, "uint32": TokenType.UINT32, "uint64": TokenType.UINT64,
    "float32": TokenType.FLOAT32, "float64": TokenType.FLOAT64, "char": TokenType.CHAR,
    "Result": TokenType.RESULT, "null": TokenType.NULL,
    "string": TokenType.STRING, "array": TokenType.ARRAY,
}
KEYWORDS = {
    "let": TokenType.LET, "free": TokenType.FREE, "def": TokenType.DEF, "struct": TokenType.STRUCT,
    "if": TokenType.IF, "else": TokenType.ELSE, "elif": TokenType.ELIF, "while": TokenType.WHILE, "for": TokenType.FOR,
    "return": TokenType.RETURN, "enum": TokenType.ENUM, "Ok": TokenType.OK, "Err": TokenType.ERR,
    "spawn": TokenType.SPAWN,
    "import": TokenType.IMPORT, "try": TokenType.TRY, "catch": TokenType.CATCH,
}
# noinspection PyDictDuplicateKeys
OPERATORS = {
    "=": TokenType.ASSIGN, "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.MULTIPLY, "/": TokenType.DIVIDE,
    "%": TokenType.MODULO,
    "==": TokenType.EQUAL, "!=": TokenType.NOT_EQUAL, ">": TokenType.GREATER_THAN, "<": TokenType.LESS_THAN,
    ">=": TokenType.GREATER_EQUAL, "<=": TokenType.LESS_EQUAL, "&": TokenType.AND, "|": TokenType.OR,
    "^": TokenType.XOR,
    "<<": TokenType.LSHIFT, ">>": TokenType.RSHIFT, "~": TokenType.BIT_NOT, "&": TokenType.POINTER_REF,
    "*": TokenType.POINTER_DEREF, ".": TokenType.DOT
}
BRACKETS = {
    "(": TokenType.LPAREN, ")": TokenType.RPAREN, "{": TokenType.LBRACE, "}": TokenType.RBRACE,
    "[": TokenType.LBRACKET, "]": TokenType.RBRACKET, ";": TokenType.SEMICOLON, ":": TokenType.COLON,
    ",": TokenType.COMMA
}


def tokenize(code: str, lsp_mode = False) -> list[Token]:
    tokens = []
    line_num = 1
    col_num = 1
    i = 0
    while i < len(code):
        char = code[i]

        # Whitespace
        if char.isspace():
            if char == '\n':
                line_num += 1
                col_num = 1
            else:
                col_num += 1
            i += 1
            continue

        # Comments (single line //)
        if code[i:i + 2] == "//":
            while i < len(code) and code[i] != '\n':
                i += 1
            continue  # Continue to next line

        # Digits
        if char.isdigit():
            num_str = ""
            is_float = False
            while i < len(code) and (code[i].isdigit() or code[i] == '.'):
                if code[i] == '.':
                    is_float = True
                num_str += code[i]
                i += 1
            token_type = TokenType.FLOAT_LITERAL if is_float else TokenType.INT_LITERAL
            tokens.append(Token(token_type, num_str, line_num, col_num))
            col_num += len(num_str)
            continue

        # Characters (single quotes)
        if char == "'":
            i += 1
            char_val = code[i]
            i += 2  # Skip char and closing quote
            tokens.append(Token(TokenType.CHAR_LITERAL, char_val, line_num, col_num))
            col_num += 3
            continue

        if char == '"':
            i += 1
            string_val = ""
            while i < len(code) and code[i] != '"':
                string_val += code[i]
                i += 1
            if i < len(code) and code[i] == '"':  # Check for closing quote
                i += 1  # Consume closing quote
                tokens.append(Token(TokenType.STRING_LITERAL, string_val, line_num, col_num))
                col_num += len(string_val) + 2  # +2 for the double quotes
                continue
            else:
                if lsp_mode:
                    raise Exception(dumps({"cause": "string", "loc": {"line": line_num, "column": col_num}}))
                raise Exception(f"Unterminated string literal starting at {line_num}:{col_num}")

        # Identifiers and Keywords
        if char.isalpha() or char == '_':
            identifier = ""
            while i < len(code) and (code[i].isalnum() or code[i] == '_'):
                identifier += code[i]
                i += 1

            if identifier in KEYWORDS:
                tokens.append(Token(KEYWORDS[identifier], identifier, line_num, col_num))
            elif identifier in DATA_TYPES:
                tokens.append(Token(DATA_TYPES[identifier], identifier, line_num, col_num))
            elif identifier == 'Result':  # Special case Result type
                tokens.append(Token(TokenType.RESULT, identifier, line_num, col_num))
            else:
                tokens.append(Token(TokenType.IDENTIFIER, identifier, line_num, col_num))
            col_num += len(identifier)
            continue

        op = code[i:i + 2]
        if op == "->":  # ARROW OPERATOR CHECK - ADDED HERE
            tokens.append(Token(TokenType.ARROW, op, line_num, col_num))
            i += 2
            col_num += 2
            continue
        if op in OPERATORS and op != '=' and op != '<' and op != '>':  # avoid misinterpreting ==, >=, <=, !=
            tokens.append(Token(OPERATORS[op], op, line_num, col_num))
            i += 2
            col_num += 2
            continue

        op = code[i]
        if op in OPERATORS:
            tokens.append(Token(OPERATORS[op], op, line_num, col_num))
            i += 1
            col_num += 1
            continue
        if op in BRACKETS:
            tokens.append(Token(BRACKETS[op], op, line_num, col_num))
            i += 1
            col_num += 1
            continue
        
        if lsp_mode:
            raise Exception(dumps({"cause": "unexpect", "char": char, "loc": {"line": line_num, "column": col_num}}))
        raise Exception(f"Unexpected character '{char}' at {line_num}:{col_num}")
    tokens.append(Token(TokenType.EOF, None, line_num, col_num))
    return tokens
