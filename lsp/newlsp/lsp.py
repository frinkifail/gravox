from json import loads
from typing import cast
from pygls.server import LanguageServer
from lsprotocol.types import * # type: ignore
import re

from grvast import ProgramNode
from lexing import tokenize
from lsp.newlsp.analysis import StaticAnalyser
from lsp.newlsp.coredata import BuiltinType, ParserException, ParserExceptionLocation, RuntimeContext
from parser import Parser

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

class NewLSP(LanguageServer):
    def __init__(self):
        super().__init__("Gravox LSP", "2.0.0")
        self.files: dict[str, str] = {} # { uri: text }
        self.ast: dict[str, ProgramNode] = {} # { uri: program }
        self.data_table: dict[str, RuntimeContext] = {}

    def evaluate_ast(self, uri: str, fallback: str = ""):
        text = self.files.get(uri)
        if not text:
            if fallback:
                text = fallback
                self.files[uri] = text
            else:
                raise FileNotFoundError()
        parser = Parser(tokenize(text), True)
        try:
            self.ast[uri] = parser.parse_program()
        except Exception as e:
            try:
                error_detail: ParserException = loads(str(e))
            except:
                raise e
            error_detail['loc'] = {"column": error_detail['loc']["column"] - 1, "line": error_detail['loc']["line"] - 1}
            self.publish_diagnostics(uri, [Diagnostic(single_range(error_detail["loc"]), f"{error_detail["fn"]}: " + (f"Unexpected {error_detail["got"]} (expected {error_detail["expect"]})" if error_detail["expect"] != "unexpected" else f"Unexpected {error_detail['got']}"))])
    
    def evaluate_runtime(self, uri: str):
        ast = self.ast.get(uri)
        if not ast:
            raise LookupError("Couldn't find AST for this file.")
        if self.data_table.get(uri):
            del self.data_table[uri]
        la = StaticAnalyser(self, uri, ast)
        # self.show_message("committing war crimes soon")
        la.eval_statement(ast)
        # self.show_message_log(str(self.data_table))
        # self.show_message_log(str(la.ls.data_table))
        # self.show_message("committing war crimes")

server = NewLSP()

@server.feature(INITIALIZE)
def on_initialise(ls: NewLSP, _: InitializeParams) -> InitializeResult:
    ls.show_message("[grvlsp] initialised")
    return InitializeResult(
        ServerCapabilities(
            text_document_sync = TextDocumentSyncKind.Full, 
            completion_provider = CompletionOptions(
                resolve_provider=False,
                trigger_characters=['.']
            )
        )
    )

@server.feature(TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: NewLSP, params: DidOpenTextDocumentParams):
    # ls.text = params.text_document.text
    ls.publish_diagnostics(params.text_document.uri, [])
    ls.files[params.text_document.uri] = params.text_document.text
    ls.evaluate_ast(params.text_document.uri, params.text_document.text)
    ls.evaluate_runtime(params.text_document.uri)

@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: NewLSP, params: DidChangeTextDocumentParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    full_text = doc.source
    # ls.show_message_log("FT: " + full_text)
    ls.publish_diagnostics(params.text_document.uri, [])
    ls.files[params.text_document.uri] = full_text
    ls.evaluate_ast(params.text_document.uri, full_text)
    ls.evaluate_runtime(params.text_document.uri)

@server.feature(TEXT_DOCUMENT_COMPLETION)
def completion(ls: NewLSP, params: CompletionParams):
    return CompletionList(
        False,
        [
            *[CompletionItem(i[0], detail=i[1], documentation=i[2], kind=CompletionItemKind.Function) for i in builtin_fns],
            *[CompletionItem(k, detail=f"{k}: {cast(RuntimeContext.VariableSymbolData, v.data).type}", kind=CompletionItemKind.Variable) for k, v in ls.data_table[params.text_document.uri].symbols.items() if v.kind == RuntimeContext.Symbol.SymbolKind.VARIABLE],
            *[CompletionItem(k, detail=f"{k}({", ".join([f"{x}: {c}" for x, c in cast(RuntimeContext.FunctionSymbolData, v.data).parameters.items()])}) -> {cast(RuntimeContext.FunctionSymbolData, v.data).return_type}", kind=CompletionItemKind.Function) for k, v in ls.data_table[params.text_document.uri].symbols.items() if v.kind == RuntimeContext.Symbol.SymbolKind.FUNCTION]
        ]
    )

def extract_word_at_position(line: str, character: int) -> str:
    for match in re.finditer(r'\b\w+\b', line):
        if match.start() <= character <= match.end():
            return match.group()
    return ""

@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: NewLSP, params: HoverParams) -> Hover | None:
    uri = params.text_document.uri
    pos = params.position

    doc = ls.workspace.get_document(uri)
    lines = doc.source.splitlines()
    if pos.line >= len(lines):
        return None

    line = lines[pos.line]
    word = extract_word_at_position(line, pos.character)
    if not word:
        return None

    # Check user-defined symbols
    symbols = ls.data_table.get(uri, RuntimeContext()).symbols
    if word in symbols:
        symbol = symbols[word]
        if symbol.kind == RuntimeContext.Symbol.SymbolKind.FUNCTION:
            func = cast(RuntimeContext.FunctionSymbolData, symbol.data)
            params_list = ", ".join(f"{k}: {v}" for k, v in func.parameters.items())
            sig = f"function {word}({params_list}): {func.return_type}"
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```ts\n{sig}\n```"))

        elif symbol.kind == RuntimeContext.Symbol.SymbolKind.VARIABLE:
            var = cast(RuntimeContext.VariableSymbolData, symbol.data)
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```ts\n{word}: {var.type}\n```"))

    # Check built-ins
    for fn, sig, docstr in builtin_fns:
        if fn == word:
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```ts\n{fn}{sig}\n```\n\n{docstr}"))

    for tname, docstr in builtin_types:
        if tname == word:
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```ts\n{tname}\n```\n\n{docstr}"))

    return None

if __name__ == "__main__":
    server.start_io()
