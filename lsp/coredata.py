from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict
from enum import Enum
from lsprotocol.types import Range

from grvast import ProgramNode
from lexing import Token

class TypeKind(Enum):
    PRIMITIVE = "primitive"
    STRUCT = "struct"
    ARRAY = "array"
    FUNCTION = "function"

class SymbolKind(Enum):
    VARIABLE = "variable"
    FUNCTION = "function"
    STRUCT = "struct"
    PARAMETER = "parameter"

@dataclass
class GravoxType:
    kind: TypeKind
    name: str
    members: dict[str, 'GravoxType'] | None = None  # for structs
    element_type: 'GravoxType | None' = None  # for arrays
    return_type: 'GravoxType | None' = None  # for functions
    parameters: 'list[GravoxType] | None' = None  # for functions

# @dataclass
# class Symbol:
#     name: str
#     type: GravoxType
#     kind: SymbolKind
#     location: Any  # Your location type from parser
#     scope: 'Scope'

# Type definitions
class LocationInfo(TypedDict):
    line: int | None
    column: int | None

class ProcessingError(TypedDict):
    stage: Literal['lexer', 'parser', 'pipeline']
    message: str
    location: LocationInfo
    severity: Literal['error', 'warning']

class SemanticDiagnostic(TypedDict):
    range: Range
    message: str
    severity: int  # 1 for error, 2 for warning
    source: str

class VariableSymbol(TypedDict):
    kind: Literal['variable']
    name: str
    type: str

class FunctionParameter(TypedDict):
    name: str
    type: str

class FunctionSymbol(TypedDict):
    kind: Literal['function']
    name: str
    parameters: list[FunctionParameter]
    return_type: NotRequired[str]

class StructField(TypedDict):
    name: str
    type: str

class StructSymbol(TypedDict):
    kind: Literal['struct']
    name: str
    fields: list[StructField]

# Union type for all symbol types
Symbol = VariableSymbol | FunctionSymbol | StructSymbol

@dataclass
class Scope:
    symbols: dict[str, Symbol]
    parent: 'Scope | None' = None
    kind: str = "block"  # 'global', 'function', 'block'

class SymbolTable(TypedDict):
    # Using string keys for symbol names
    pass

# We need to extend SymbolTable to allow string indexing
class SymbolTableDict(dict[str, Symbol]):
    pass

class ProcessingResult(TypedDict):
    tokens: list[Token] | None  # You might want to define a proper Token type here
    ast: ProgramNode | None
    diagnostics: list[SemanticDiagnostic]
    symbols: SymbolTableDict
    errors: list[ProcessingError]