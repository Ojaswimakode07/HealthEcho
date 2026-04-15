from __future__ import annotations

from importlib.machinery import SourcelessFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path


def load_current_module(module_name: str, file_path: str, package: str | None = None) -> dict:
    path = Path(file_path)
    root = next((parent for parent in path.parents if (parent / "bytecode_backup").exists()), path.parents[1])
    pyc_path = root / "bytecode_backup" / path.relative_to(root).parent / "__pycache__" / f"{path.stem}.cpython-312.pyc"
    loader = SourcelessFileLoader(module_name, str(pyc_path))
    spec = spec_from_loader(module_name, loader)
    if spec is None:
        raise ImportError(f"Unable to build import spec for {module_name}")
    if package is not None:
        spec.submodule_search_locations = [str(path.parent)]
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module.__dict__
