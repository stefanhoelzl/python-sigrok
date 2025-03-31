from collections.abc import Iterator

import pytest

from sigrok import Sigrok


def test_host_build_info() -> None:
    assert isinstance(Sigrok.get_host_build_info(), str)


def test_libs_build_info() -> None:
    for name, version in Sigrok.get_libs_build_info().items():
        assert isinstance(name, str), name
        assert isinstance(version, str), version


def test_get_scpi_backends_build_info() -> None:
    assert isinstance(Sigrok.get_scpi_backends_build_info(), str)


class TestInitialization:
    def test_init_exit(self) -> None:
        sr = Sigrok()
        sr.init()
        sr.exit()

    def test_double_init(self) -> None:
        sr = Sigrok()
        sr.init()
        sr.init()

    def test_reinit(self) -> None:
        sr = Sigrok()
        sr.init()
        sr.exit()
        sr.init()

    def test_exit_without_init(self) -> None:
        sr = Sigrok()
        sr.exit()

    def test_context(self) -> None:
        with Sigrok():
            pass

    def test_del(self) -> None:
        sr = Sigrok()
        del sr


@pytest.fixture
def sr() -> Iterator[Sigrok]:
    with Sigrok() as sigrok:
        yield sigrok
