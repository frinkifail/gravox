from typing import TYPE_CHECKING, Any
from grvast import ASTNode, ProgramNode
from lsp.coredata import GravoxType, Scope, Symbol, SymbolKind, TypeKind
if TYPE_CHECKING:
    from lsp.lsp import SemanticDiagnostic
from lsprotocol.types import Range, Position


class GravoxSemanticAnalyzer:
    def __init__(self) -> None:
        self.global_scope: Scope = Scope(symbols={}, kind="global")
        self.current_scope: Scope = self.global_scope
        self.diagnostics: list['SemanticDiagnostic'] = []
        self.symbol_table: dict[str, dict[str, Any]] = {}  # Flat symbol table for LSP queries
        self.builtin_types: dict[str, GravoxType] = {}
        self.builtin_functions: dict[str, Symbol] = {}
        self._initialize_builtins()
    
    def _initialize_builtins(self) -> None:
        """Initialize built-in types and functions"""
        # Built-in types
        self.builtin_types.update({
            'string': GravoxType(TypeKind.PRIMITIVE, 'string'),
            'int8': GravoxType(TypeKind.PRIMITIVE, 'int8'),
            'null': GravoxType(TypeKind.PRIMITIVE, 'null'),
            'Array': GravoxType(TypeKind.PRIMITIVE, 'Array'),
        })
        
        # Built-in functions
        print_type: GravoxType = GravoxType(TypeKind.FUNCTION, 'print', 
                                           return_type=GravoxType(TypeKind.PRIMITIVE, 'null'))
        self.builtin_functions['print'] = Symbol(
            'print', print_type, SymbolKind.FUNCTION, None, self.global_scope
        )
        
        input_type: GravoxType = GravoxType(TypeKind.FUNCTION, 'input',
                                           return_type=GravoxType(TypeKind.PRIMITIVE, 'string'))
        self.builtin_functions['input'] = Symbol(
            'input', input_type, SymbolKind.FUNCTION, None, self.global_scope
        )
        
        fore_type: GravoxType = GravoxType(TypeKind.FUNCTION, 'fore',
                                          return_type=GravoxType(TypeKind.PRIMITIVE, 'string'))
        self.builtin_functions['fore'] = Symbol(
            'fore', fore_type, SymbolKind.FUNCTION, None, self.global_scope
        )
        
        style_type: GravoxType = GravoxType(TypeKind.FUNCTION, 'style',
                                           return_type=GravoxType(TypeKind.PRIMITIVE, 'string'))
        self.builtin_functions['style'] = Symbol(
            'style', style_type, SymbolKind.FUNCTION, None, self.global_scope
        )
        
        clear_screen_type: GravoxType = GravoxType(TypeKind.FUNCTION, 'clear_screen',
                                                  return_type=GravoxType(TypeKind.PRIMITIVE, 'null'))
        self.builtin_functions['clear_screen'] = Symbol(
            'clear_screen', clear_screen_type, SymbolKind.FUNCTION, None, self.global_scope
        )
        
        raw_print_type: GravoxType = GravoxType(TypeKind.FUNCTION, 'raw_print',
                                               return_type=GravoxType(TypeKind.PRIMITIVE, 'null'))
        self.builtin_functions['raw_print'] = Symbol(
            'raw_print', raw_print_type, SymbolKind.FUNCTION, None, self.global_scope
        )
    
    def analyze(self, ast: ProgramNode) -> list['SemanticDiagnostic']:
        """Main entry point - returns LSP-compatible diagnostics"""
        self.diagnostics = []
        self.symbol_table = {}
        
        if ast:
            self.visit(ast)
        
        return self.diagnostics
    
    def get_symbol_table(self) -> dict[str, dict[str, Any]]:
        """Return symbol table for LSP queries"""
        return self.symbol_table
    
    def visit(self, node: ASTNode) -> GravoxType:
        """Generic visitor dispatch"""
        method_name: str = f'visit_{node.__class__.__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node: ASTNode) -> GravoxType:
        """Default visitor for unknown nodes"""
        # Handle different node types that might have children
        if hasattr(node, 'children'):
            for child in node.children:
                self.visit(child)
        elif hasattr(node, 'body'):
            for child in node.body:
                self.visit(child)
        elif hasattr(node, 'statements'):
            for child in node.statements:
                self.visit(child)
        # Return a default type for expressions
        return self.builtin_types.get('null', GravoxType(TypeKind.PRIMITIVE, 'null'))
    
    def visit_AllocStatement(self, node: Any) -> None:
        """Handle 'alloc variable: type = value' statements"""
        # Check if variable already exists in current scope
        if node.name in self.current_scope.symbols:
            self.add_error(f"Variable '{node.name}' already declared", node.location)
            return
        
        # Determine type
        var_type: GravoxType | None = None
        if hasattr(node, 'type_annotation') and node.type_annotation:
            var_type = self.resolve_type(node.type_annotation)
        elif hasattr(node, 'initializer') and node.initializer:
            var_type = self.infer_type(node.initializer)
        else:
            self.add_error(f"Cannot infer type for '{node.name}'", node.location)
            return
        
        # Validate initializer type if present
        if hasattr(node, 'initializer') and node.initializer:
            init_type: GravoxType = self.visit(node.initializer)
            if not self.is_assignable(init_type, var_type):
                self.add_error(f"Cannot assign {init_type.name} to {var_type.name}", 
                             node.location)
        
        # Add to symbol table
        symbol: Symbol = Symbol(node.name, var_type, SymbolKind.VARIABLE, 
                               node.location, self.current_scope)
        self.current_scope.symbols[node.name] = symbol
        
        # Also add to flat symbol table for LSP
        if hasattr(node, 'location'):
            self.symbol_table[node.name] = {
                'name': node.name,
                'type': var_type.name,
                'kind': 'variable',
                'location': node.location,
                'scope': self.current_scope.kind
            }
    
    def visit_StructDef(self, node: Any) -> None:
        """Handle struct definitions"""
        if node.name in self.current_scope.symbols:
            self.add_error(f"Struct '{node.name}' already defined", node.location)
            return
        
        # Create struct type with members
        members: dict[str, GravoxType] = {}
        for field in node.fields:
            field_type: GravoxType = self.resolve_type(field.type)
            members[field.name] = field_type
        
        struct_type: GravoxType = GravoxType(TypeKind.STRUCT, node.name, members=members)
        symbol: Symbol = Symbol(node.name, struct_type, SymbolKind.STRUCT, 
                               node.location, self.current_scope)
        self.current_scope.symbols[node.name] = symbol
        
        # Add to flat symbol table
        self.symbol_table[node.name] = {
            'name': node.name,
            'type': 'struct',
            'kind': 'struct',
            'location': node.location,
            'scope': self.current_scope.kind,
            'fields': [f.name for f in node.fields]
        }
    
    def visit_MemberAccess(self, node: Any) -> GravoxType:
        """Handle obj.member access"""
        obj_type: GravoxType = self.visit(node.object)
        assert obj_type.members

        if obj_type.kind == TypeKind.STRUCT:
            if node.member not in obj_type.members:
                self.add_error(f"'{obj_type.name}' has no member '{node.member}'", 
                             node.location)
                return self.error_type()
            return obj_type.members[node.member]
        
        # Handle built-in method calls
        if obj_type.name == 'Array' and self.is_array_method(node.member):
            return self.get_array_method_type(node.member, obj_type)
        
        if obj_type.name == 'string' and self.is_string_method(node.member):
            return self.get_string_method_type(node.member, obj_type)
        
        self.add_error(f"Cannot access member '{node.member}' on type '{obj_type.name}'", 
                      node.location)
        return self.error_type()
    
    def visit_FunctionCall(self, node: Any) -> GravoxType:
        """Handle function calls"""
        # Look up function symbol
        symbol: Symbol | None = self.lookup_symbol(node.name)
        
        if not symbol or symbol.kind != SymbolKind.FUNCTION:
            self.add_error(f"'{node.name}' is not a function", node.location)
            return self.error_type()
        
        # Check argument count
        expected_params: list[GravoxType] = symbol.type.parameters or []
        if len(node.arguments) != len(expected_params):
            self.add_error(f"Expected {len(expected_params)} arguments, "
                          f"got {len(node.arguments)}", node.location)
        
        # Type check arguments
        for i, (arg, expected_type) in enumerate(zip(node.arguments, expected_params)):
            arg_type: GravoxType = self.visit(arg)
            if not self.is_assignable(arg_type, expected_type):
                self.add_error(f"Argument {i+1} type mismatch: "
                              f"expected {expected_type.name}, got {arg_type.name}", 
                              arg.location)
        
        return symbol.type.return_type or self.error_type()
    
    def visit_TypeCast(self, node: Any) -> GravoxType:
        """Handle <type>expression casts"""
        source_type: GravoxType = self.visit(node.expression)
        target_type: GravoxType = self.resolve_type(node.target_type)
        
        if not self.is_valid_cast(source_type, target_type):
            self.add_error(f"Cannot cast from '{source_type.name}' to '{target_type.name}'", 
                          node.location)
        
        return target_type
    
    def visit_Identifier(self, node: Any) -> GravoxType:
        """Handle variable/function references"""
        symbol: Symbol | None = self.lookup_symbol(node.name)
        if not symbol:
            self.add_error(f"Undefined symbol '{node.name}'", node.location)
            return self.error_type()
        return symbol.type
    
    def visit_StringLiteral(self, node: Any) -> GravoxType:
        """Handle string literals"""
        return self.builtin_types['string']
    
    def visit_IntegerLiteral(self, node: Any) -> GravoxType:
        """Handle integer literals"""
        return self.builtin_types['int8']
    
    def visit_BinaryOperation(self, node: Any) -> GravoxType:
        """Handle binary operations like +, -, ==, etc."""
        left_type: GravoxType = self.visit(node.left)
        right_type: GravoxType = self.visit(node.right)
        
        # Simple type checking for binary operations
        if node.operator in ['+', '-', '*', '/', '%']:
            if left_type.name == 'int8' and right_type.name == 'int8':
                return self.builtin_types['int8']
            elif left_type.name == 'string' and right_type.name == 'string' and node.operator == '+':
                return self.builtin_types['string']
            else:
                self.add_error(f"Cannot apply {node.operator} to {left_type.name} and {right_type.name}", 
                              node.location)
                return self.error_type()
        
        elif node.operator in ['==', '!=', '<', '>', '<=', '>=']:
            if left_type.name == right_type.name:
                return self.builtin_types['int8']  # Gravox uses int8 for booleans
            else:
                self.add_error(f"Cannot compare {left_type.name} and {right_type.name}", 
                              node.location)
                return self.error_type()
        
        return self.error_type()
    
    def resolve_type(self, type_node: Any) -> GravoxType:
        """Resolve a type annotation to a GravoxType"""
        if hasattr(type_node, 'name'):
            type_name: str = type_node.name
        else:
            type_name = str(type_node)
        
        # Check built-in types
        if type_name in self.builtin_types:
            return self.builtin_types[type_name]
        
        # Check user-defined types (structs)
        symbol: Symbol | None = self.lookup_symbol(type_name)
        if symbol and symbol.kind == SymbolKind.STRUCT:
            return symbol.type
        
        # Unknown type
        self.add_error(f"Unknown type '{type_name}'", getattr(type_node, 'location', None))
        return self.error_type()
    
    def infer_type(self, node: Any) -> GravoxType:
        """Infer type from an expression"""
        return self.visit(node)
    
    def is_assignable(self, source: GravoxType, target: GravoxType) -> bool:
        """Check if source type can be assigned to target type"""
        return source.name == target.name or source.name == 'error'
    
    def is_valid_cast(self, source: GravoxType, target: GravoxType) -> bool:
        """Check if source type can be cast to target type"""
        # Allow casting between primitive types
        primitive_types: set[str] = {'string', 'int8'}
        return (source.name in primitive_types and target.name in primitive_types) or \
               source.name == 'error' or target.name == 'error'
    
    def get_array_method_type(self, method_name: str, array_type: GravoxType) -> GravoxType:
        """Get return type for Array methods"""
        if method_name == 'len':
            return self.builtin_types['int8']
        elif method_name == 'push':
            return self.builtin_types['null']
        elif method_name == 'get':
            # Return element type (simplified - assume mixed type array)
            return self.builtin_types['string']  # Default to string for now
        elif method_name == 'to_array':
            return array_type  # Return the array itself
        else:
            return self.error_type()
    
    def get_string_method_type(self, method_name: str, string_type: GravoxType) -> GravoxType:
        """Get return type for String methods"""
        if method_name == 'split':
            return GravoxType(TypeKind.ARRAY, 'Array', element_type=self.builtin_types['string'])
        else:
            return self.error_type()
    
    def error_type(self) -> GravoxType:
        """Return an error type for error recovery"""
        return GravoxType(TypeKind.PRIMITIVE, 'error')
    
    def lookup_symbol(self, name: str) -> Symbol | None:
        """Look up symbol in current scope chain"""
        scope: Scope | None = self.current_scope
        while scope:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        
        # Check builtins
        if name in self.builtin_functions:
            return self.builtin_functions[name]
        
        return None
    
    def is_array_method(self, method_name: str) -> bool:
        return method_name in ['len', 'push', 'get', 'to_array']
    
    def is_string_method(self, method_name: str) -> bool:
        return method_name in ['split']
    
    def location_to_range(self, location: Position) -> Range:
        """Convert location to LSP Range format"""
        if location is None:
            # Default range for built-ins or missing location info
            return {
                'start': {'line': 0, 'character': 0},
                'end': {'line': 0, 'character': 1}
            }
        
        # Adapt this based on your location format
        # Assuming location has line/column attributes
        if hasattr(location, 'line') and hasattr(location, 'column'):
            return Range(
                # {'line': location['line'] or 0, 'character': location['column'] or 0},
                location,
                location
            )
        elif isinstance(location, dict):
            return Range(location, location)
        else:
            # Fallback
            return Range(Position(0, 0), Position(0, 0))
    
    def add_error(self, message: str, location: Any) -> None:
        self.diagnostics.append({
            'severity': 1,  # Error
            'range': self.location_to_range(location),
            'message': message,
            'source': 'gravox'
        })
    
    def enter_scope(self, scope_kind: str = "block") -> Scope:
        """Enter a new scope"""
        new_scope: Scope = Scope(symbols={}, parent=self.current_scope, kind=scope_kind)
        self.current_scope = new_scope
        return new_scope
    
    def exit_scope(self) -> None:
        """Exit current scope"""
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent
    
    def visit_FunctionDef(self, node: Any) -> None:
        """Handle function definitions"""
        if node.name in self.current_scope.symbols:
            self.add_error(f"Function '{node.name}' already defined", node.location)
            return
        
        # Create function type
        param_types: list[GravoxType] = []
        for param in node.parameters:
            param_type: GravoxType = self.resolve_type(param.type)
            param_types.append(param_type)
        
        return_type: GravoxType = (self.resolve_type(node.return_type) 
                                  if node.return_type 
                                  else self.builtin_types['null'])
        
        func_type: GravoxType = GravoxType(TypeKind.FUNCTION, node.name, 
                                          parameters=param_types, return_type=return_type)
        symbol: Symbol = Symbol(node.name, func_type, SymbolKind.FUNCTION, 
                               node.location, self.current_scope)
        self.current_scope.symbols[node.name] = symbol
        
        # Enter function scope
        func_scope: Scope = self.enter_scope("function")
        
        # Add parameters to function scope
        for param in node.parameters:
            param_type = self.resolve_type(param.type)
            param_symbol: Symbol = Symbol(param.name, param_type, SymbolKind.PARAMETER,
                                        param.location, func_scope)
            func_scope.symbols[param.name] = param_symbol
        
        # Visit function body
        if hasattr(node, 'body'):
            for stmt in node.body:
                self.visit(stmt)
        
        # Exit function scope
        self.exit_scope()
        
        # Add to flat symbol table
        self.symbol_table[node.name] = {
            'name': node.name,
            'type': 'function',
            'kind': 'function',
            'location': node.location,
            'scope': self.current_scope.kind,
            'return_type': return_type.name,
            'parameters': [{'name': p.name, 'type': self.resolve_type(p.type).name} for p in node.parameters]
        }