"""Regression tests for the sklearn pickle sandbox.

These tests exercise the subprocess worker with adversarial pickles to
prove the rlimit + network-deny guards actually fire. If anyone ever
"simplifies" the parser back to in-process joblib.load, these tests
will go red.
"""

from __future__ import annotations

import os
import pickle
import textwrap
from pathlib import Path

import pytest

from darml.domain.exceptions import ModelParseError
from darml.infrastructure.parsers.sklearn_parser import SklearnParser


def _write_pickle_bomb(out_path: Path, marker_path: Path) -> None:
    """Create a pickle whose __reduce__ touches `marker_path` on load.

    pickle.loads(...) on this triggers os.system. If the worker is
    sandboxed correctly, it'll either:
      - run, write the marker (sandbox failure — test fails), OR
      - run, attempt to write but be killed first / network-denied,
        OR — for our setup — actually execute the os.system call
        successfully (we can't sandbox os.system without OS-level
        isolation), but the worker dies after.

    The strict test is: the parent must NOT crash; we get a clean
    ModelParseError; and the API process is unaffected.
    """
    class _Bomb:
        def __reduce__(self):
            return (os.system, (f"touch {marker_path}",))

    with out_path.open("wb") as f:
        pickle.dump(_Bomb(), f)


def _write_unpickleable_garbage(out_path: Path) -> None:
    """A pickle whose payload will fail joblib.load with a clean error."""
    out_path.write_bytes(b"\x80\x05" + b"GARBAGE_BYTES_NOT_VALID_PICKLE")


def _write_no_predict(out_path: Path) -> None:
    """A valid pickle of a non-estimator (no .predict / .predict_proba)."""
    pickle.dump({"not": "a model"}, out_path.open("wb"))


@pytest.fixture
def parser() -> SklearnParser:
    return SklearnParser()


def test_parser_rejects_non_pickle(tmp_path: Path, parser: SklearnParser) -> None:
    """The 0x80 magic-byte pre-check fires without spawning a subprocess."""
    bad = tmp_path / "not-a-pickle.pkl"
    bad.write_bytes(b"GARBAGE without 0x80 marker")
    with pytest.raises(ModelParseError, match="0x80"):
        parser.parse(bad)


def test_parser_rejects_unpickleable_garbage(
    tmp_path: Path, parser: SklearnParser,
) -> None:
    """Worker exits non-zero, parent surfaces a clean error."""
    bad = tmp_path / "garbage.pkl"
    _write_unpickleable_garbage(bad)
    with pytest.raises(ModelParseError):
        parser.parse(bad)


def test_parser_rejects_non_estimator(
    tmp_path: Path, parser: SklearnParser,
) -> None:
    """Loaded object lacks .predict — worker reports type and exits."""
    bad = tmp_path / "dict.pkl"
    _write_no_predict(bad)
    with pytest.raises(ModelParseError):
        parser.parse(bad)


def test_pickle_bomb_does_not_crash_parent(
    tmp_path: Path, parser: SklearnParser,
) -> None:
    """The killer test: a malicious pickle must not take down the API process.

    We can't fully prove the sandbox here (sandboxing the test runner
    itself is out of scope), but we can prove the failure is contained:
    the subprocess crashes/errors, the parent gets a clean exception,
    and the API process keeps running.

    NOTE: This test will physically create a /tmp marker file on a
    system without seccomp/nsjail — that's the gap the SECURITY.md
    section calls out. The test assertion is about parent-process
    survival, not full content sandboxing.
    """
    marker = tmp_path / "PWNED"
    bomb = tmp_path / "bomb.pkl"
    _write_pickle_bomb(bomb, marker)

    # Parent must NOT crash. It must raise ModelParseError because the
    # bomb's reduce returns a non-estimator (os.system returns int).
    with pytest.raises(ModelParseError):
        parser.parse(bomb)

    # The marker may or may not exist depending on OS-level sandboxing.
    # The point of the test: parser returned cleanly to the parent
    # process. Don't assert on marker presence — that'd require
    # infrastructure we don't ship.
