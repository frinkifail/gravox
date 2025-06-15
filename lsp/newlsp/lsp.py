from json import loads
from typing import cast
from pygls.server import LanguageServer
from lsprotocol.types import * # type: ignore

from grvast import ProgramNode
from lexing import tokenize
from lsp.newlsp.analysis import StaticAnalyser
from lsp.newlsp.coredata import BuiltinType, ParserException, ParserExceptionLocation, RuntimeContext
from parser import Parser

# (name, syntax (detail), docs)
builtin_fns: list[tuple[str, str, str]] = [
    ("print", "(...val: string) -> null", "Prints the message(s) to stdout.")
]

# (name, docs)
builtin_types: list[BuiltinType] = [
    ("string", "A string of characters.")
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

    def evaluate_ast(self, uri: str):
        text = self.files.get(uri)
        if not text:
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
        del self.data_table[uri]
        la = StaticAnalyser(self, uri, ast)
        la.eval_statement(ast)
        self.show_message("commiting war crimes")

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
    ls.files[params.text_document.uri] = params.text_document.text
    ls.evaluate_ast(params.text_document.uri)
    ls.evaluate_runtime(params.text_document.uri)

@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: NewLSP, params: DidChangeTextDocumentParams):
    new_text = params.content_changes[0].text
    print(new_text)
    ls.files[params.text_document.uri] = new_text
    ls.evaluate_ast(params.text_document.uri)
    ls.evaluate_runtime(params.text_document.uri)

@server.feature(TEXT_DOCUMENT_COMPLETION)
def completion(ls: NewLSP, params: CompletionParams):
    return CompletionList(
        False,
        [
            *[CompletionItem(i[0], detail=i[1], documentation=i[2], kind=CompletionItemKind.Function) for i in builtin_fns],
            *[CompletionItem(k, detail=f"{k}: {cast(RuntimeContext.VariableSymbolData, v.symbols[k].data).type}") for k, v in ls.data_table.items() if v.symbols[k].kind == v.Symbol.SymbolKind.VARIABLE]
        ]
    )

@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: NewLSP, params: HoverParams):
    pass

if __name__ == "__main__":
    server.start_io()
