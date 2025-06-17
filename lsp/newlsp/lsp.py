import builtins
from json import loads
from typing import cast
from pygls.server import LanguageServer
from lsprotocol.types import * # type: ignore
import re

from grvast import ProgramNode
from lexing import tokenize
from lsp.newlsp.analysis import StaticAnalyser
from lsp.newlsp.coredata import ParserException, RuntimeContext, single_range, builtin_fns, builtin_types
from parser import Parser

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
        try:
            parser = Parser(tokenize(text, True), True)
        except Exception as e:
            try:
                error = loads(str(e))
            except:
                raise e
            error['loc'] = {"column": error['loc']["column"] - 1, "line": error['loc']["line"] - 1}
            self.publish_diagnostics(uri, [Diagnostic(single_range(error["loc"]), f"{f'Unexpected character: {error["char"]}' if error["cause"] == "unexpect" else "Unterminated string literal"}")])
            return
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
        return la

    def get_struct_members(self, struct_name: str, uri: str) -> list[CompletionItem]:
        """Get completion items for struct members (fields and methods)"""
        completions = []
        
        symbols = self.data_table.get(uri, RuntimeContext()).symbols
        if struct_name not in symbols:
            return completions
            
        symbol = symbols[struct_name]
        if symbol.kind != RuntimeContext.Symbol.SymbolKind.STRUCT:
            return completions
            
        struct_data = cast(RuntimeContext.StructSymbolData, symbol.data)
        # self.show_message_log(str(struct_data))
        
        # Add struct fields
        # if hasattr(struct_data, 'fields'):
        for field_name, field_type in struct_data.fields.items():
            completions.append(CompletionItem(
                label=field_name,
                detail=f"{field_name}: {field_type}",
                kind=CompletionItemKind.Field
            ))
        
        # Add struct methods
        # if hasattr(struct_data, 'methods'):
        for method_name, method_data in struct_data.methods.items():
            params_list = ", ".join(f"{k}: {v}" for k, v in method_data.parameters.items())
            completions.append(CompletionItem(
                label=method_name,
                detail=f"{method_name}({params_list}) -> {method_data.return_type}",
                kind=CompletionItemKind.Method
            ))
        
        return completions

    def find_variable_type_at_position(self, uri: str, line: str, character: int) -> str | None:
        """Find the type of a variable before the dot at the given position"""
        # Extract text before the dot
        text_before_dot = line[:character-1]  # -1 to exclude the dot
        
        # Find the last word (variable name) before the dot
        match = re.search(r'(\w+)$', text_before_dot.strip())
        if not match:
            return None
            
        var_name = match.group(1)
        
        # Look up the variable in the symbol table
        symbols = self.data_table.get(uri, RuntimeContext()).symbols
        if var_name not in symbols:
            return None
            
        symbol = symbols[var_name]
        if symbol.kind == RuntimeContext.Symbol.SymbolKind.VARIABLE:
            var_data = cast(RuntimeContext.VariableSymbolData, symbol.data)
            return var_data.type
            
        return None

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
    la = ls.evaluate_runtime(params.text_document.uri)
    ls.publish_diagnostics(params.text_document.uri, la.diagnostics)

@server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: NewLSP, params: DidChangeTextDocumentParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    full_text = doc.source
    # ls.show_message_log("FT: " + full_text)
    ls.publish_diagnostics(params.text_document.uri, [])
    ls.files[params.text_document.uri] = full_text
    ls.evaluate_ast(params.text_document.uri, full_text)
    la = ls.evaluate_runtime(params.text_document.uri)
    ls.publish_diagnostics(params.text_document.uri, la.diagnostics)

@server.feature(TEXT_DOCUMENT_COMPLETION, CompletionOptions(['.']))
def completion(ls: NewLSP, params: CompletionParams):
    uri = params.text_document.uri
    position = params.position
    
    # Get the current line
    doc = ls.workspace.get_document(uri)
    lines = doc.source.splitlines()
    
    if position.line >= len(lines):
        return CompletionList(False, [])
    
    current_line = lines[position.line]
    
    # Check if we're completing after a dot
    if position.character > 0 and current_line[position.character - 1] == '.':
        # This is struct member completion
        var_type = ls.find_variable_type_at_position(uri, current_line, position.character)
        if var_type:
            struct_completions = ls.get_struct_members(var_type, uri)
            return CompletionList(False, struct_completions)
        else:
            # No completions if we can't determine the type
            return CompletionList(False, [])
    
    # Regular completion (not after a dot)
    symbols = ls.data_table.get(uri, RuntimeContext()).symbols if uri in ls.data_table else {}
    
    return CompletionList(
        False,
        [
            *[CompletionItem(i[0], detail=i[1], documentation=i[2], kind=CompletionItemKind.Function) for i in builtin_fns],
            *[CompletionItem(i[0], documentation=i[1], kind=CompletionItemKind.Class) for i in builtin_types],
            *[CompletionItem(k, detail=f"{k}: {cast(RuntimeContext.VariableSymbolData, v.data).type}", kind=CompletionItemKind.Variable) for k, v in symbols.items() if v.kind == RuntimeContext.Symbol.SymbolKind.VARIABLE],
            *[CompletionItem(k, detail=f"{k}({", ".join([f"{x}: {c}" for x, c in cast(RuntimeContext.FunctionSymbolData, v.data).parameters.items()])}) -> {cast(RuntimeContext.FunctionSymbolData, v.data).return_type}", kind=CompletionItemKind.Function) for k, v in symbols.items() if v.kind == RuntimeContext.Symbol.SymbolKind.FUNCTION],
            *[CompletionItem(k, kind=CompletionItemKind.Struct) for k, v in symbols.items() if v.kind == v.SymbolKind.STRUCT]
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
            sig = f"{word}({params_list}) -> {func.return_type}"
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```py\n{sig}\n```"))

        elif symbol.kind == RuntimeContext.Symbol.SymbolKind.VARIABLE:
            var = cast(RuntimeContext.VariableSymbolData, symbol.data)
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```py\n{word}: {var.type}\n```"))
        
        elif symbol.kind == RuntimeContext.Symbol.SymbolKind.STRUCT:
            var = cast(RuntimeContext.StructSymbolData, symbol.data)
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```c\nstruct {word}\n```"))

    # Check built-ins
    for fn, sig, docstr in builtin_fns:
        if fn == word:
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```py\n{fn}{sig}\n```\n\n{docstr}"))

    for tname, docstr in builtin_types:
        if tname == word:
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"```py\n{tname}\n```\n\n{docstr}"))

    return None

if __name__ == "__main__":
    server.start_io()