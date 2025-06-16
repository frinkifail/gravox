import json
import os
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, Any, Callable

from colored import back, fore, style

if TYPE_CHECKING:
    from gravox import Interpreter

class Stdlib:
    def __init__(self, interpreter: "Interpreter"):
        self.interpreter = interpreter

    def print(self, args: list[Any]): # TODO: pretty
        print(*args)
        if self.interpreter.resolving_context == "colour":
            print(end=style("reset"))
            self.interpreter.resolving_context = "normal"

    @staticmethod
    def debug_print(args: list[Any]):
        print(args)
    
    @staticmethod
    def raw_print(args: list[Any]):
        print(*args, end="")

    @staticmethod
    def input(args: tuple[str]):
        return input(args[0])

    def gravox_heapusage(self, _):
        return self.interpreter.next_memory_address

    def gravox_heapsize(self, _):
        return self.interpreter.heap_size

    def gravox_dump_heap(self, _):
        return self.interpreter.memory

    @staticmethod
    def clear_screen(_):
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")

    @staticmethod
    def _array_push(args: list[Any]):
        array = args[0]
        value = args[1]
        try:
            array.append(value)
        except Exception as e:
            print(f"info: {value} -> {array}")
            print("tip: you might be trying to create an array using inline assignment\n"
                  "tip: (e.g. 'let x = Array([...]);')\n"
                  "tip: This is not supported. Create the array on a different line instead.")
            raise e
        return array

    @staticmethod
    def _file_exec(args: tuple[str, str, str | None]): # (file, mode, arg)
        data = None
        if args[1] == "e":
            return Path(args[0]).exists()
        with open(args[0], args[1]) as f:
            match args[1]:
                case "w+":
                    f.write(args[2])
                    data = True
                case "r":
                    data = f.read()
                case _:
                    raise Exception("No such mode for file execution.")
        return data

    @staticmethod
    def _json_exec(args: tuple[str, dict | str | None]): # (op, contents)
        match args[0]:
            case "dump":
                return json.dumps(args[1])
            case "load":
                return json.loads(str(args[1]))
            case _:
                raise Exception("Unknown operation")

    @staticmethod
    def _get_nth_element(args: tuple[list[Any], int]):
        # print(args)
        return args[0][args[1]]

    @staticmethod
    def len(args: tuple[list[Any] | str]):
        return len(args[0])

    @staticmethod
    def split(args: tuple[str, str]):
        return args[0].split(args[1])

    @staticmethod
    def get_time_ms(_):
        return int(round(time() * 1000))
    
    def fore(self, args: tuple[str]):
        self.interpreter.resolving_context = "colour"
        return fore(args[0])

    def back(self, args: tuple[str]):
        self.interpreter.resolving_context = "colour"
        return back(args[0])

    def style(self, args: tuple[str]):
        self.interpreter.resolving_context = "colour"
        if args[0] == "reset":
            self.interpreter.resolving_context = "normal"
        return style(args[0])

    def __getitem__(self, item) -> Callable | None:
        try:
            clsitem = self.__getattribute__(item)
        except AttributeError:
            clsitem = None
        if clsitem and callable(clsitem):
            return clsitem
        else:
            return None