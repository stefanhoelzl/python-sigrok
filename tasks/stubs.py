import builtins
import importlib
import textwrap
from collections.abc import Iterator
from pathlib import Path
from typing import TypeVar

from invoke import Context, task
from pyclibrary.c_parser import Type as CType

from tasks.dev import format_and_lint


def indent(line: str, *, n: int = 1) -> str:
    return textwrap.indent(line, "    " * n)


T = TypeVar("T")


def only_public(items: dict[str, T]) -> Iterator[tuple[str, T]]:
    for name, value in items.items():
        if name.startswith("_"):
            continue
        yield name, value


def value_annotations(values: dict[str, CType]) -> Iterator[str]:
    for name, value in only_public(values):
        if value is None:
            yield f"{name}: None"
        elif isinstance(value, (str, float, int)):
            yield f"{name}: {type(value).__name__}"
        else:
            error = f"unknown value type: {name}={value}"
            raise ValueError(error)


def function_annotations(funcs: dict[str, CType]) -> Iterator[str]:
    def param_annotations(params: CType) -> Iterator[str]:
        for declarator in params:
            if (name := declarator[0]) is None:
                continue

            safe_name = f"{name}_" if name in ["in", *dir(builtins)] else name
            yield f"{safe_name}: Any = None"

    def return_type_annotation(return_ctype: CType) -> str:
        return_type = return_ctype.type_spec
        return {"void": "None", "int": "int", "char": "str"}.get(return_type, "None")

    for name, func in only_public(funcs):
        ret = return_type_annotation(func.type_spec)
        params = param_annotations(func.declarators[0])
        yield f"def {name}(self, {','.join(params)}) -> CallResult[{ret}]: ..."


def struct_annotations(structs: dict[str, CType]) -> Iterator[str]:
    for name, _struct in only_public(structs):
        yield f"class {name}(NamedTuple): ..."


def type_annotations(types: dict[str, CType]) -> Iterator[str]:
    for name, typ in only_public(types):
        if len(typ.declarators) == 0:
            yield f"{name}: None"


def enum_annotations(enums: dict[str, dict[str, int]]) -> Iterator[str]:
    for name, enum in only_public(enums):
        if len(enum) > 0:
            yield f"class {name}(TypedDict):"
            for field in enum:
                yield indent(f"{field}: int")
            yield f"class __{name}_enum__(IntEnum):"
            for field in enum:
                yield indent(f"{field}: int")


@task
def gen(ctx: Context, clib: str) -> None:
    module_name, var_name = clib.split(":")
    module = importlib.import_module(module_name)
    lib = getattr(module, var_name)
    definitions = lib._headers_.defs

    stub_path = Path(module.__file__ or "stub.py").with_suffix(".pyi")
    with stub_path.open(mode="w") as stub:
        stub.write(
            textwrap.dedent(
                """
                from enum import IntEnum
                from typing import Any, NamedTuple, Generic, TypeVar, TypedDict
                _R = TypeVar("_R")
                class CallResult(Generic[_R]):
                    rval: _R
                    def __getitem__(self, item: str) -> Any: ...
                """
            )
        )
        stub.write(
            "\n".join(
                (
                    f"class {var_name.upper()}:",
                    *map(indent, value_annotations(definitions["values"])),
                    *map(indent, function_annotations(definitions["functions"])),
                    *map(indent, type_annotations(definitions["types"])),
                    *map(indent, struct_annotations(definitions["structs"])),
                    *map(indent, enum_annotations(definitions["enums"])),
                    f"{var_name}: {var_name.upper()}",
                )
            )
        )

    format_and_lint(ctx, single_file=str(stub_path))


@task
def bindings(ctx: Context) -> None:
    gen(ctx, "sigrok.bindings:lib")
