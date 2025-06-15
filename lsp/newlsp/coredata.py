from dataclasses import dataclass, field
from enum import Enum
from typing import TypeAlias, TypedDict

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
        pass # TODO: TBA
    @dataclass
    class Symbol:
        class SymbolKind(Enum):
            VARIABLE = "variable"
            FUNCTION = "function"
            STRUCT = "struct"
        name: str
        kind: SymbolKind
        data: AnySymbolData
    symbols: dict[str, Symbol] = field(default_factory=dict) # { name: sym }