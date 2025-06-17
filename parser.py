from json import dumps
from typing import cast
from grvast import ASTNode, MethodCallNode, StructFieldAccessNode, StringLiteralNode, IdentifierNode, CharLiteralNode, \
    FloatLiteralNode, IntLiteralNode, NullLiteralNode, UnaryOpNode, BinaryOpNode, SpawnTaskNode, VarAssignNode, \
    EnumDefNode, StructDefNode, TypeCastNode, ForLoopNode, WhileLoopNode, IfStatementNode, ReturnNode, FunctionCallNode, \
    FunctionDefNode, FreeMemoryNode, LetMemoryNode, BlockNode, ProgramNode, ImportNode, TryNode, \
    ArrayLiteralNode, ArrayIndexNode
from lexing import Token, TokenType, DATA_TYPES

class Parser:
    def __init__(self, tokens: list[Token], lsp_mode = False):
        self.tokens = tokens
        self.current_token_index = 0
        self.lsp_mode = lsp_mode

    def peek(self, offset=0) -> Token | None:
        index = self.current_token_index + offset
        if index < len(self.tokens):
            return self.tokens[index]
        return None

    def consume(self, token_type):
        token = self.current_token()
        if token.type == token_type:
            self.current_token_index += 1
            return token
        if self.lsp_mode:
            raise Exception(dumps({"fn": "consume", "expect": repr(token_type), "got": repr(token.type), "loc": {'line': token.line, 'column': token.column}}))
        raise Exception(f"Expected token type {token_type}, but got {token.type} at {token.line}:{token.column}")

    def consume_data_type(self):
        token = self.current_token()
        if token.type in [
            *DATA_TYPES.values(),
            TokenType.IDENTIFIER # Also allow generic IDENTIFIER for custom types
        ]:
            self.consume(token.type)
            return token
        if self.lsp_mode:
            raise Exception(dumps({"fn": "consume_data_type", "expect": "datatype", "got": repr(token.type), "loc": {'line': token.line, 'column': token.column}}))
        raise Exception(f"Expected data type, but got {token.type} at {token.line}:{token.column}")

    def current_token(self):
        if self.current_token_index < len(self.tokens):
            return self.tokens[self.current_token_index]
        return self.tokens[-1] # EOF token

    def parse_program(self):
        statements = []
        while self.current_token().type != TokenType.EOF:
            statements.append(self.parse_statement())
        node = ProgramNode(statements)
        node.line = statements[0].line if statements else 1 - 1
        node.column = statements[0].column if statements else 1 - 1
        return node

    def parse_block(self):
        lbrace = self.consume(TokenType.LBRACE)
        statements = []
        while self.current_token().type != TokenType.RBRACE:
            statements.append(self.parse_statement())
        self.consume(TokenType.RBRACE)
        node = BlockNode(statements)
        node.line = lbrace.line - 1
        node.column = lbrace.column - 1
        return node

    def parse_import(self):
        import_token = self.consume(TokenType.IMPORT)
        module_name = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.SEMICOLON)
        node = ImportNode(module_name.value)
        node.line = import_token.line - 1
        node.column = import_token.column - 1
        return node

    def parse_statement(self):
        token = self.current_token()
        peek = self.peek(1)
        assert peek is not None

        if token.type == TokenType.LET:
            return self.parse_variable_declaration()
        elif token.type == TokenType.FREE:
            return self.parse_memory_free()
        elif token.type == TokenType.DEF:
            return self.parse_function_definition()
        elif token.type == TokenType.STRUCT:
            return self.parse_struct_definition()
        elif token.type == TokenType.ENUM:
            return self.parse_enum_definition()
        elif token.type == TokenType.IF:
            return self.parse_if_statement()
        elif token.type == TokenType.WHILE:
            return self.parse_while_loop()
        elif token.type == TokenType.FOR:
            return self.parse_for_loop()
        elif token.type == TokenType.RETURN:
            return self.parse_return_statement()
        elif token.type == TokenType.IDENTIFIER and peek.type == TokenType.ASSIGN:
            return self.parse_variable_assignment()
        elif token.type == TokenType.IDENTIFIER and peek.type == TokenType.LPAREN:
            return self.parse_function_call_statement()  # Function call as a statement
        elif token.type == TokenType.IDENTIFIER and peek.type == TokenType.DOT:
            return self.parse_struct_field_assignment_or_access()  # For struct field assignment like vec.x = 10;
        elif token.type == TokenType.SPAWN:
            return self.parse_spawn_task()
        elif token.type == TokenType.IMPORT:
            return self.parse_import()
        elif token.type == TokenType.TRY:
            return self.parse_try_statement()

        # Default to an expression statement (like a function call, method call, or assignment)
        expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        return expr

    def parse_try_statement(self):
        try_token = self.consume(TokenType.TRY)
        try_block = self.parse_block()
        catch_block = None
        if self.current_token().type == TokenType.CATCH:
            self.consume(TokenType.CATCH)
            catch_block = self.parse_block()
        node = TryNode(try_block, catch_block)
        node.line = try_token.line - 1
        node.column = try_token.column - 1
        return node

    def parse_variable_declaration(self):
        let_token = self.consume(TokenType.LET)
        var_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.COLON)
        data_type_token = self.consume_data_type()
        value_expr = None
        if self.current_token().type == TokenType.ASSIGN:
            self.consume(TokenType.ASSIGN)
            value_expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        node = LetMemoryNode(var_name_token.value, data_type_token.value, value_expr)
        node.line = let_token.line - 1
        node.column = let_token.column - 1
        return node

    def parse_memory_free(self):
        free_token = self.consume(TokenType.FREE)
        var_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.SEMICOLON)
        node = FreeMemoryNode(var_name_token.value)
        node.line = free_token.line - 1
        node.column = free_token.column - 1
        return node

    def parse_variable_assignment(self):
        var_name_token = self.consume(TokenType.IDENTIFIER)
        assign_token = self.consume(TokenType.ASSIGN)
        value_expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        node = VarAssignNode(var_name_token.value, value_expr)
        node.line = var_name_token.line - 1
        node.column = var_name_token.column - 1
        return node

    def parse_function_definition(self):
        def_token = self.consume(TokenType.DEF)
        func_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.LPAREN)
        params = []
        if self.current_token().type != TokenType.RPAREN:
            param_name_token = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            param_type_token = self.consume_data_type()
            params.append((param_name_token.value, param_type_token.value))
            while self.current_token().type == TokenType.COMMA:
                self.consume(TokenType.COMMA)
                param_name_token = self.consume(TokenType.IDENTIFIER)
                self.consume(TokenType.COLON)
                param_type_token = self.consume_data_type()
                params.append((param_name_token.value, param_type_token.value))
        self.consume(TokenType.RPAREN)
        self.consume(TokenType.ARROW)
        return_type_token = self.consume_data_type()
        body = self.parse_block()
        node = FunctionDefNode(func_name_token.value, params, return_type_token.value, body)
        node.line = def_token.line - 1
        node.column = def_token.column - 1
        return node

    def parse_function_call_statement(self):  # Function call used as statement (e.g., function());
        func_call = self.parse_postfix_expression()  # This will handle the function call
        self.consume(TokenType.SEMICOLON)
        # func_call already has line/column
        return func_call

    def parse_return_statement(self):
        return_token = self.consume(TokenType.RETURN)
        return_expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        node = ReturnNode(return_expr)
        node.line = return_token.line - 1
        node.column = return_token.column - 1
        return node

    def parse_if_statement(self):
        if_token = self.consume(TokenType.IF)
        condition = self.parse_expression()
        then_block = self.parse_block()
        elif_blocks = []
        else_block = None
        while self.current_token().type == TokenType.ELIF:
            elif_token = self.consume(TokenType.ELIF)
            elif_condition = self.parse_expression()
            elif_block = self.parse_block()
            elif_blocks.append((elif_condition, elif_block))
        if self.current_token().type == TokenType.ELSE:
            self.consume(TokenType.ELSE)
            else_block = self.parse_block()
        node = IfStatementNode(condition, then_block, else_block, elif_blocks)
        node.line = if_token.line - 1
        node.column = if_token.column - 1
        return node

    def parse_while_loop(self):
        while_token = self.consume(TokenType.WHILE)
        condition = self.parse_expression()
        loop_block = self.parse_block()
        node = WhileLoopNode(condition, loop_block)
        node.line = while_token.line - 1
        node.column = while_token.column - 1
        return node

    def parse_for_loop(self):
        for_token = self.consume(TokenType.FOR)
        self.consume(TokenType.LPAREN)
        init_stmt = self.parse_statement()
        condition_expr = self.parse_expression()
        self.consume(TokenType.SEMICOLON)
        increment_stmt = self.parse_statement()
        self.consume(TokenType.RPAREN)
        loop_block = self.parse_block()
        node = ForLoopNode(init_stmt, condition_expr, increment_stmt, loop_block)
        node.line = for_token.line - 1
        node.column = for_token.column - 1
        return node

    def parse_type_cast(self):
        lt_token = self.consume(TokenType.LESS_THAN)
        target_type_token = self.consume_data_type()
        self.consume(TokenType.GREATER_THAN)
        expression = self.parse_atom()
        node = TypeCastNode(target_type_token.value, expression)
        node.line = lt_token.line - 1
        node.column = lt_token.column - 1
        return node

    def parse_struct_definition(self):
        struct_token = self.consume(TokenType.STRUCT)
        struct_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.LBRACE)
        fields = []
        functions = []
        while self.current_token().type != TokenType.RBRACE:
            if (peek := self.peek()) and peek.type == TokenType.DEF:
                functions.append(self.parse_function_definition())
            else:
                field_name_token = self.consume(TokenType.IDENTIFIER)
                self.consume(TokenType.COLON)
                field_type_token = self.consume_data_type()
                self.consume(TokenType.SEMICOLON)
                fields.append((field_name_token.value, field_type_token.value))
        self.consume(TokenType.RBRACE)
        node = StructDefNode(struct_name_token.value, fields, functions)
        node.line = struct_token.line - 1
        node.column = struct_token.column - 1
        return node

    def parse_enum_definition(self):
        enum_token = self.consume(TokenType.ENUM)
        enum_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.LBRACE)
        members = []
        while self.current_token().type != TokenType.RBRACE:
            member_name_token = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COMMA)
            members.append(member_name_token.value)
        self.consume(TokenType.RBRACE)
        node = EnumDefNode(enum_name_token.value, members)
        node.line = enum_token.line - 1
        node.column = enum_token.column - 1
        return node

    def parse_spawn_task(self):
        spawn_token = self.consume(TokenType.SPAWN)
        self.consume(TokenType.IDENTIFIER) # consume 'task' keyword
        task_name_token = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.LPAREN)
        params = []
        if self.current_token().type != TokenType.RPAREN:
            param_name_token = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            param_type_token = self.consume(TokenType.IDENTIFIER)
            params.append((param_name_token.value, param_type_token.value))
            while self.current_token().type == TokenType.COMMA:
                self.consume(TokenType.COMMA)
                param_name_token = self.consume(TokenType.IDENTIFIER)
                self.consume(TokenType.COLON)
                param_type_token = self.consume(TokenType.IDENTIFIER)
                params.append((param_name_token.value, param_type_token.value))
        self.consume(TokenType.RPAREN)
        body = self.parse_block()
        node = SpawnTaskNode(task_name_token.value, params, body)
        node.line = spawn_token.line - 1
        node.column = spawn_token.column - 1
        return node

    # --- Expression Parsing (Precedence Climbing) ---
    def parse_expression(self):
        return self.parse_bitwise_or()

    def parse_bitwise_or(self):
        left_expr = self.parse_bitwise_xor()
        while self.current_token().type == TokenType.OR:
            op_token = self.consume(TokenType.OR)
            right_expr = self.parse_bitwise_xor()
            node = BinaryOpNode(op_token.type, left_expr, right_expr)
            node.line = op_token.line - 1
            node.column = op_token.column - 1
            left_expr = node
        return left_expr

    def parse_bitwise_xor(self):
        left_expr = self.parse_bitwise_and()
        while self.current_token().type == TokenType.XOR:
            op_token = self.consume(TokenType.XOR)
            right_expr = self.parse_bitwise_and()
            node = BinaryOpNode(op_token.type, left_expr, right_expr)
            node.line = op_token.line - 1
            node.column = op_token.column - 1
            left_expr = node
        return left_expr

    def parse_bitwise_and(self):
        left_expr = self.parse_equality()
        while self.current_token().type == TokenType.AND:
            op_token = self.consume(TokenType.AND)
            right_expr = self.parse_equality()
            node = BinaryOpNode(op_token.type, left_expr, right_expr)
            node.line = op_token.line - 1
            node.column = op_token.column - 1
            left_expr = node
        return left_expr

    def parse_equality(self):
        left_expr = self.parse_comparison()
        while self.current_token().type in (TokenType.EQUAL, TokenType.NOT_EQUAL):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_comparison()
            node = BinaryOpNode(op_token.type, left_expr, right_expr)
            node.line = op_token.line - 1
            node.column = op_token.column - 1
            left_expr = node
        return left_expr

    def parse_comparison(self):
        left_expr = self.parse_shift()
        while self.current_token().type in (TokenType.GREATER_THAN, TokenType.LESS_THAN, TokenType.GREATER_EQUAL, TokenType.LESS_EQUAL):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_shift()
            node = BinaryOpNode(op_token.type, left_expr, right_expr)
            node.line = op_token.line - 1
            node.column = op_token.column - 1
            left_expr = node
        return left_expr

    def parse_shift(self):
        left_expr = self.parse_term()
        while self.current_token().type in (TokenType.LSHIFT, TokenType.RSHIFT):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_term()
            node = BinaryOpNode(op_token.type, left_expr, right_expr)
            node.line = op_token.line - 1
            node.column = op_token.column - 1
            left_expr = node
        return left_expr

    def parse_term(self):
        left_expr = self.parse_factor()
        while self.current_token().type in (TokenType.PLUS, TokenType.MINUS):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_factor()
            node = BinaryOpNode(op_token.type, left_expr, right_expr)
            node.line = op_token.line - 1
            node.column = op_token.column - 1
            left_expr = node
        return left_expr

    def parse_factor(self):
        left_expr = self.parse_unary()
        while self.current_token().type in (TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO):
            op_token = self.consume(self.current_token().type)
            right_expr = self.parse_unary()
            node = BinaryOpNode(op_token.type, left_expr, right_expr)
            node.line = op_token.line - 1
            node.column = op_token.column - 1
            left_expr = node
        return left_expr

    def parse_unary(self):
        if self.current_token().type in (TokenType.MINUS, TokenType.BIT_NOT, TokenType.POINTER_DEREF, TokenType.POINTER_REF):
            op_token = self.consume(self.current_token().type)
            expr = self.parse_unary() # Apply unary to the result of another unary
            node = UnaryOpNode(op_token.type, expr)
            node.line = op_token.line - 1
            node.column = op_token.column - 1
            return node
        return self.parse_postfix_expression()

    def parse_struct_field_assignment_or_access(self):
        # Use postfix expression parsing to handle method calls and field access
        expr = self.parse_postfix_expression()

        # Check if this is an assignment (for field assignments like struct.field = value)
        if isinstance(expr, StructFieldAccessNode) and self.current_token().type == TokenType.ASSIGN:
            assign_token = self.consume(TokenType.ASSIGN)
            value_expr = self.parse_expression()
            self.consume(TokenType.SEMICOLON)
            node = VarAssignNode(f"{expr.struct_var_name}.{expr.field_name}", value_expr)
            node.line = assign_token.line - 1
            node.column = assign_token.column - 1
            return node
        else:
            # This is either a method call or field access - consume semicolon and return
            self.consume(TokenType.SEMICOLON)
            # expr already has line/column
            return expr

    def parse_postfix_expression(self):
        # First, parse the primary part of the expression (the "atom").
        node = self.parse_atom()

        # Then, loop to parse any postfix operators like (), [], or .
        while True:
            if self.current_token().type == TokenType.LPAREN:
                lparen = self.consume(TokenType.LPAREN)
                args = []
                if self.current_token().type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.current_token().type == TokenType.COMMA:
                        self.consume(TokenType.COMMA)
                        args.append(self.parse_expression())
                self.consume(TokenType.RPAREN)
                # 'node' becomes the callee of the function call
                call_node = FunctionCallNode(cast(IdentifierNode, node), args)
                call_node.line = lparen.line - 1
                call_node.column = lparen.column - 1
                node = call_node
            elif self.current_token().type == TokenType.LBRACKET:
                lbracket = self.consume(TokenType.LBRACKET)
                index_expr = self.parse_expression()
                self.consume(TokenType.RBRACKET)
                index_node = ArrayIndexNode(node, index_expr)
                index_node.line = lbracket.line - 1
                index_node.column = lbracket.column - 1
                node = index_node
            elif self.current_token().type == TokenType.DOT:
                dot_token = self.consume(TokenType.DOT)
                if (peek := self.peek()) and peek.type == TokenType.INT_LITERAL:
                    member_name_token = self.consume(TokenType.INT_LITERAL)
                else:
                    member_name_token = self.consume(TokenType.IDENTIFIER)
                if self.current_token().type == TokenType.LPAREN:
                    lparen = self.consume(TokenType.LPAREN)
                    args = []
                    if self.current_token().type != TokenType.RPAREN:
                        args.append(self.parse_expression())
                        while self.current_token().type == TokenType.COMMA:
                            self.consume(TokenType.COMMA)
                            args.append(self.parse_expression())
                    self.consume(TokenType.RPAREN)
                    method_node = MethodCallNode(node, member_name_token.value, args)
                    method_node.line = dot_token.line - 1
                    method_node.column = dot_token.column - 1
                    node = method_node
                else:
                    if isinstance(node, IdentifierNode):
                        field_node = StructFieldAccessNode(node.name, member_name_token.value)
                    else:
                        field_node = StructFieldAccessNode(node, member_name_token.value)
                    field_node.line = dot_token.line - 1
                    field_node.column = dot_token.column - 1
                    node = field_node
            else:
                break # No more postfix operators
        return node

    def parse_atom(self):
        token = self.current_token()

        if token.type == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            # expr already has line/column
            return expr
        elif token.type == TokenType.INT_LITERAL:
            tok = self.consume(TokenType.INT_LITERAL)
            node = IntLiteralNode(tok.value)
            node.line = tok.line - 1
            node.column = tok.column - 1
            return node
        elif token.type == TokenType.FLOAT_LITERAL:
            tok = self.consume(TokenType.FLOAT_LITERAL)
            node = FloatLiteralNode(tok.value)
            node.line = tok.line - 1
            node.column = tok.column - 1
            return node
        elif token.type == TokenType.CHAR_LITERAL:
            tok = self.consume(TokenType.CHAR_LITERAL)
            node = CharLiteralNode(tok.value)
            node.line = tok.line - 1
            node.column = tok.column - 1
            return node
        elif token.type == TokenType.STRING_LITERAL:
            tok = self.consume(TokenType.STRING_LITERAL)
            node = StringLiteralNode(tok.value)
            node.line = tok.line - 1
            node.column = tok.column - 1
            return node
        elif token.type == TokenType.NULL:
            tok = self.consume(TokenType.NULL)
            node = NullLiteralNode()
            node.line = tok.line - 1
            node.column = tok.column - 1
            return node
        elif token.type == TokenType.IDENTIFIER:
            tok = self.consume(TokenType.IDENTIFIER)
            node = IdentifierNode(tok.value)
            node.line = tok.line - 1
            node.column = tok.column - 1
            return node
        elif token.type == TokenType.LESS_THAN and (peek := self.peek(1)) and peek.type in DATA_TYPES.values():
            return self.parse_type_cast()
        elif token.type == TokenType.LBRACKET:
            return self.parse_array_literal()
        else:
            if self.lsp_mode:
                raise Exception(dumps({"fn": "parse_atom", "expect": "unexpected", "got": repr(token.type), "loc": {'line': token.line, 'column': token.column}}))
            raise Exception(f"Unexpected token {token.type} in expression at {token.line}:{token.column}")

    def parse_array_literal(self):
        lbracket = self.consume(TokenType.LBRACKET)
        elements = []
        if self.current_token().type != TokenType.RBRACKET:
            elements.append(self.parse_expression())
            while self.current_token().type == TokenType.COMMA:
                self.consume(TokenType.COMMA)
                elements.append(self.parse_expression())
        self.consume(TokenType.RBRACKET)
        node = ArrayLiteralNode(elements)
        node.line = lbracket.line - 1
        node.column = lbracket.column - 1
        return node
