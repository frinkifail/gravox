from interpreter import Interpreter
from lexing import tokenize
from parser import Parser

# --- 2. Parser (Simplified - Expression parsing and basic statements) ---
# [MOVED]

# --- 3. Interpreter ---
# [MOVED]

interpreter = None
ast_tree = None

# --- 4. Example Execution ---
def run_gravox_code(code, debug = False):
    global interpreter, ast_tree
    try:
        tokens = tokenize(code)
        if debug:
            print("\nTokens:")
            for token in tokens:
                print(token)

        parser = Parser(tokens)
        ast_tree = parser.parse_program()
        if debug:
            print("\nAST Tree:")
            print(ast_tree)

        interpreter = Interpreter(8_000_000)
        interpreter.interpret(ast_tree)
        # if debug:
        #     print("\nInterpretation Result:", result)
        # return result

    except Exception as e:
        if debug:
            raise e
        assert interpreter
        print(f"error at {interpreter.last_updated_index} ({interpreter.last_node}): {e}")
        return None

if __name__ == "__main__":
    from sys import argv
    with open(argv[1]) as f:
        run_gravox_code(f.read(), "-d" in argv)
