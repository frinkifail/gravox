from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias, TypedDict
from lsprotocol.types import Position, Range

from lexing import Token

class ParserExceptionLocation(TypedDict):
    line: int
    column: int

class ParserException(TypedDict):
    fn: str
    expect: str | Token
    got: Token
    loc: ParserExceptionLocation

BuiltinType = tuple[str, str]
AnySymbolData: TypeAlias = "RuntimeContext.VariableSymbolData | RuntimeContext.FunctionSymbolData | RuntimeContext.StructSymbolData"

@dataclass
class RuntimeContext:
    @dataclass
    class VariableSymbolData:
        type: str
    @dataclass
    class FunctionSymbolData:
        parameters: dict[str, BuiltinType | str] # { param_name: type }
        return_type: BuiltinType | str
    @dataclass
    class StructSymbolData:
        fields: dict[str, BuiltinType | str]
        methods: dict[str, "RuntimeContext.FunctionSymbolData"]
    @dataclass
    class Symbol:
        class SymbolKind(Enum):
            VARIABLE = "variable"
            FUNCTION = "function"
            STRUCT = "struct"
        name: str
        kind: SymbolKind
        data: AnySymbolData
        dont_complete = False # If True, this symbol will not be included in autocompletion suggestions
    symbols: dict[str, Symbol] = field(default_factory=dict) # { name: sym }

# (name, syntax (detail), docs)
builtin_fns: list[tuple[str, str, str]] = [
    ("print", "(...val: string) -> null", "Prints the message(s) to stdout."),
    ("debug_print", "(...val: string) -> null", "Prints the message(s) to stdout, useful for debugging."),
    ("raw_print", "(...val: string) -> null", "Prints the message(s) to stdout without a newline at the end."),
    ("input", "(prompt: string) -> string", "Prompts the user for input and returns it as a string."),
    ("gravox_heapusage", "() -> number", "Returns the current heap usage in bytes."),
    ("gravox_heapsize", "() -> number", "Returns the total heap size in bytes."),
    ("gravox_dump_heap", "() -> any[]", "Dumps the current heap memory as an array."),
    ("clear_screen", "() -> null", "Clears the console screen."),
    ("_array_push", "(array: any[], value: any) -> null", "[INTERNAL]: Use `Array.push` from `stdlib`."),
    ("_file_exec", "(file: string, mode: string, arg: string?) -> any", "[INTERNAL]: Use `fs` from `stdlib`."),
    ("_json_exec", "(op: string, contents: any) -> any", "[INTERNAL]: Use `json` from `stdlib`."),
    ("_get_nth_element", "(array: any[], index: int<any>) -> any", "[INTERNAL]: Use `Array.get` from `stdlib`."),
    ("len", "(array: any[] | string) -> int", "Returns the length of the object."),
    ("split", "(string: string, separator: string) -> string[]", "Splits a string into an array of substrings based on the separator."),
    ("get_time_ms", "() -> int", "Returns the current time in high-resolution milliseconds since the epoch."),
    ("fore", "(color: string) -> null", "Sets the foreground color for console output."),
    ("back", "(color: string) -> null", "Sets the background color for console output."),
    ("style", "(style: string) -> null", "Sets the text style for console output (e.g., bold, italic, reset).")
]

# (name, docs)
builtin_types: list[BuiltinType] = [
    ("string", "A string of characters."),
    ("int8", "An 8-bit signed integer."),
    ("int16", "A 16-bit signed integer."),
    ("int32", "A 32-bit signed integer."),
    ("int64", "A 64-bit signed integer."),
    ("uint8", "An 8-bit unsigned integer."),
    ("uint16", "A 16-bit unsigned integer."),
    ("uint32", "A 32-bit unsigned integer."),
    ("uint64", "A 64-bit unsigned integer."),
    ("float32", "A 32-bit floating-point number."),
    ("float64", "A 64-bit floating-point number."),
    ("char", "A single character."),
    ("array", "An array of elements of any type."),
    ("Result", "[Deprecated]: Use `try/catch`. A result type that can be either a success or an error."),
    ("null", "A null value, representing the absence of a value.")
]

def single_range(pos: Position | ParserExceptionLocation):
    if isinstance(pos, dict):
        pos = Position(pos["line"], pos["column"])
    return Range(pos, pos)
