from pathlib import Path

ProjectPath = Path(__file__).parent.parent
PyProjectPath = ProjectPath / "pyproject.toml"
SrcPath = ProjectPath / "src"
ModulePath = SrcPath / "sigrok"
TestsPath = ProjectPath / "tests"
