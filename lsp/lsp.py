# gravox_lsp.py
import re
import traceback
from typing import Any
from pygls.server import LanguageServer
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DIAGNOSTIC,
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    CompletionParams,
    Diagnostic,
    DiagnosticSeverity,
    DocumentDiagnosticParams,
    FullDocumentDiagnosticReport,
    Hover,
    HoverParams,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
)

# Import your existing components
from grvast import ProgramNode
from lexing import tokenize  # Your existing lexer
from lsp.coredata import FunctionParameter, LocationInfo, ProcessingError, ProcessingResult, SemanticDiagnostic, StructField, Symbol, SymbolTableDict
from parser import Parser  # Your existing parser
from lsp.semantics import GravoxSemanticAnalyzer  # The semantic analyzer we built



def parse_unexpected_token(error_msg: str) -> tuple[str, int | None, int | None]:
    """
    Parse error message like: "Unexpected token TokenType.RBRACE in expression at 120:5"
    Returns: (message, line, column) or (message, None, None) if can't parse
    """
    if not error_msg.startswith("Unexpected token"):
        raise RuntimeError("[Internal] That's not an unexpected token error.")
    # Pattern to match "at line:column" at the end
    pattern: str = r'^(.+?)\s+at\s+(\d+):(\d+)$'
    match = re.match(pattern, error_msg)
    
    if match:
        message: str = match.group(1).strip()
        line: int = int(match.group(2)) - 1  # Convert to 0-based
        column: int = int(match.group(3)) - 1  # Convert to 0-based
        return message, line, column
    
    # If pattern doesn't match, return the whole message
    return error_msg, None, None

class GravoxLanguageProcessor:
    """Handles the complete lexing → parsing → analysis pipeline"""
    
    def __init__(self) -> None:
        # self.lexer = GravoxLexer()
        self.parser: Parser = Parser([])
        self.analyzer: GravoxSemanticAnalyzer = GravoxSemanticAnalyzer()
    
    def process_document(self, source_code: str) -> ProcessingResult:
        """Complete pipeline: source → tokens → AST → diagnostics"""
        result: ProcessingResult = {
            'tokens': None,
            'ast': None,
            'diagnostics': [],
            'symbols': SymbolTableDict(),
            'errors': []
        }
        
        try:
            # Step 1: Tokenize
            tokens = tokenize(source_code)
            result['tokens'] = tokens
            
            # Handle lexer errors
            # if hasattr(self.lexer, 'errors') and self.lexer.errors:
            #     for error in self.lexer.errors:
            #         result['errors'].append({
            #             'stage': 'lexer',
            #             'message': error.message,
            #             'location': error.location,
            #             'severity': 'error'
            #         })
            
            # Step 2: Parse (only if tokenization succeeded)
            if tokens and not result['errors']:
                self.parser.tokens = tokens
                try:
                    ast: ProgramNode = self.parser.parse_program()
                    result['ast'] = ast
                except Exception as e:
                    if str(e).startswith("Unexpected token"):
                        parsed_error: tuple[str, int | None, int | None] = parse_unexpected_token(str(e))
                        error: ProcessingError = {
                            'stage': 'parser',
                            'message': str(e),
                            'location': {'line': parsed_error[1], 'column': parsed_error[2]},
                            'severity': 'error'
                        }
                        result['errors'].append(error)
                
                # Handle parser errors
                # if hasattr(self.parser, 'errors') and self.parser.errors:
                #     for error in self.parser.errors:
                #         result['errors'].append({
                #             'stage': 'parser',
                #             'message': error.message,
                #             'location': error.location,
                #             'severity': 'error'
                #         })
            
            # Step 3: Semantic Analysis (only if parsing succeeded)
            if result['ast'] and not result['errors']:
                diagnostics: list[SemanticDiagnostic] = self.analyzer.analyze(result['ast'])
                result['diagnostics'] = diagnostics
                # Note: get_symbol_table() doesn't exist according to the comment
                # You'll need to implement this method in GravoxSemanticAnalyzer
                result['symbols'] = self.analyzer.get_symbol_table()
                
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            filename, line, func, text = tb[-1]  # Get the last frame
            error: ProcessingError = {
                'stage': 'pipeline',
                'message': f"Processing error: {str(e)} ({filename}@{func} : {line} ({text}))",
                'location': {'line': 0, 'column': 0},
                'severity': 'error'
            }
            result['errors'].append(error)
        
        return result
    
    def get_completions_at_position(self, source_code: str, position: Position) -> list[CompletionItem]:
        """Get completions at a specific position"""
        try:
            # Process up to cursor position for context
            lines: list[str] = source_code.split('\n')
            cursor_line: str = lines[position.line] if position.line < len(lines) else ""
            
            # Basic keyword completions
            items: list[CompletionItem] = self._get_keyword_completions()
            
            # Try to get context-aware completions
            result: ProcessingResult = self.process_document(source_code)
            if result['symbols']:
                items.extend(self._get_symbol_completions(result['symbols'], position))
            
            return items
            
        except Exception as e:
            # Return basic completions on error
            return self._get_keyword_completions()
    
    def _get_keyword_completions(self) -> list[CompletionItem]:
        """Basic keyword completions"""
        keywords: list[str] = [
            'let', 'def', 'struct', 'if', 'elif', 'else', 
            'while', 'for', 'return', 'import', 'null'
        ]
        
        items: list[CompletionItem] = []
        for keyword in keywords:
            items.append(CompletionItem(
                label=keyword,
                kind=CompletionItemKind.Keyword,
                detail=f"Gravox keyword"
            ))
        
        # Built-in functions
        builtins: list[tuple[str, str, str]] = [
            ('print', 'Print to console', '(message)'),
            ('input', 'Read user input', '(prompt)'),
            ('fore', 'Set foreground color', '(color)'),
            ('style', 'Set text style', '(style)'),
            ('clear_screen', 'Clear the screen', '()'),
            ('raw_print', 'Print without newline', '(message)'),
        ]
        
        for name, detail, signature in builtins:
            items.append(CompletionItem(
                label=name,
                kind=CompletionItemKind.Function,
                detail=detail,
                insert_text=f"{name}{signature}",
                documentation=detail
            ))
        
        # Built-in types
        types: list[tuple[str, str]] = [
            ('string', 'String type'),
            ('int8', '8-bit integer type'),
            ('Array', 'Dynamic array type'),
        ]
        
        for type_name, detail in types:
            items.append(CompletionItem(
                label=type_name,
                kind=CompletionItemKind.Class,
                detail=detail
            ))
        
        return items
    
    def _get_symbol_completions(self, symbols: SymbolTableDict, position: Position) -> list[CompletionItem]:
        """Get completions based on symbols in scope"""
        items: list[CompletionItem] = []
        
        for symbol_name, symbol in symbols.items():
            if symbol['kind'] == 'variable':
                items.append(CompletionItem(
                    label=symbol_name,
                    kind=CompletionItemKind.Variable,
                    detail=f"{symbol['type']} variable",
                    documentation=f"Variable of type {symbol['type']}"
                ))
            elif symbol['kind'] == 'function':
                return_type = symbol.get('return_type', 'null')
                items.append(CompletionItem(
                    label=symbol_name,
                    kind=CompletionItemKind.Function,
                    detail=f"Function → {return_type}",
                    documentation=f"User-defined function"
                ))
            elif symbol['kind'] == 'struct':
                field_names = [field['name'] for field in symbol['fields']]
                items.append(CompletionItem(
                    label=symbol_name,
                    kind=CompletionItemKind.Struct,
                    detail="User-defined struct",
                    documentation=f"Struct with fields: {', '.join(field_names)}"
                ))
        
        return items
    
    def get_hover_info(self, source_code: str, position: Position) -> str | None:
        """Get hover information at position"""
        try:
            result: ProcessingResult = self.process_document(source_code)
            
            # You'll need to implement position-to-symbol mapping
            # This is a simplified version
            symbol: Symbol | None = self._get_symbol_at_position(result, position)
            
            if symbol:
                return self._format_symbol_hover(symbol)
            
        except Exception:
            pass
        
        return None
    
    def _get_symbol_at_position(self, result: ProcessingResult, position: Position) -> Symbol | None:
        """Find symbol at specific position - you'll need to implement this based on your AST"""
        # This is where you'd traverse your AST to find the symbol at the given position
        # For now, returning None - you'll implement based on your AST structure
        return None
    
    def _format_symbol_hover(self, symbol: Symbol) -> str:
        """Format symbol information for hover"""
        if symbol['kind'] == 'variable':
            return f"**{symbol['name']}**: `{symbol['type']}`\n\nVariable"
        elif symbol['kind'] == 'function':
            params: list[FunctionParameter] = symbol['parameters']
            param_str: str = ', '.join([f"{p['name']}: {p['type']}" for p in params])
            return_type = symbol.get('return_type', 'null')
            return f"**{symbol['name']}**(`{param_str}`) → `{return_type}`\n\nFunction"
        elif symbol['kind'] == 'struct':
            fields: list[StructField] = symbol['fields']
            field_str: str = '\n'.join([f"- {f['name']}: {f['type']}" for f in fields])
            return f"**{symbol['name']}**\n\nStruct:\n{field_str}"
        
        return f"**{symbol['name']}**"

class GravoxLanguageServer(LanguageServer):
    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.processor: GravoxLanguageProcessor = GravoxLanguageProcessor()

gravox_server: GravoxLanguageServer = GravoxLanguageServer('gravox-lsp', 'v0.1.0')

@gravox_server.feature(TEXT_DOCUMENT_DIAGNOSTIC)
def diagnostic(params: DocumentDiagnosticParams) -> FullDocumentDiagnosticReport:
    """Provide diagnostics for a document"""
    document = gravox_server.workspace.get_document(params.text_document.uri)
    
    # Process the document through the complete pipeline
    result: ProcessingResult = gravox_server.processor.process_document(document.source)
    
    # Convert errors and diagnostics to LSP format
    lsp_diagnostics: list[Diagnostic] = []
    
    # Add lexer/parser errors
    for error in result['errors']:
        severity: DiagnosticSeverity = (DiagnosticSeverity.Error 
                                       if error['severity'] == 'error' 
                                       else DiagnosticSeverity.Warning)
        
        # Convert your location format to LSP Range
        location: LocationInfo = error['location']
        range_obj: Range = Range(
            start=Position(line=location['line'] or 0, character=location['column'] or 0),
            end=Position(line=location['line'] or 0, character=(location['column'] or 0) + 1)
        )
        
        lsp_diagnostics.append(Diagnostic(
            range=range_obj,
            message=f"[{error['stage']}] {error['message']}",
            severity=severity,
            source='gravox'
        ))
    
    # Add semantic analysis diagnostics
    for diag in result['diagnostics']:
        lsp_diagnostics.append(Diagnostic(
            range=diag['range'],
            message=diag['message'],
            severity=DiagnosticSeverity.Error if diag['severity'] == 1 else DiagnosticSeverity.Warning,
            source='gravox'
        ))
    
    return FullDocumentDiagnosticReport(
        kind="full",
        items=lsp_diagnostics
    )

@gravox_server.feature(TEXT_DOCUMENT_COMPLETION)
def completion(params: CompletionParams) -> CompletionList:
    """Provide completion items"""
    document = gravox_server.workspace.get_document(params.text_document.uri)
    
    items: list[CompletionItem] = gravox_server.processor.get_completions_at_position(
        document.source, params.position
    )
    
    return CompletionList(is_incomplete=False, items=items)

@gravox_server.feature(TEXT_DOCUMENT_HOVER)
def hover(params: HoverParams) -> Hover | None:
    """Provide hover information"""
    document = gravox_server.workspace.get_document(params.text_document.uri)
    
    hover_text: str | None = gravox_server.processor.get_hover_info(
        document.source, params.position
    )
    
    if hover_text:
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.Markdown,
                value=hover_text
            )
        )
    
    return None

if __name__ == '__main__':
    print("[gravoxlsp] started")
    gravox_server.start_io()