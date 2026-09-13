"""Typed boundary conversion (WP1#1) — strict, no string-truthiness."""
import math

import pytest

from server.optimisation_demo import coerce
from server.optimisation_demo.coerce import CoercionError


def test_as_bool_accepts_real_and_string_forms():
    assert coerce.as_bool(True) is True
    assert coerce.as_bool(False) is False
    assert coerce.as_bool("true") is True
    assert coerce.as_bool("false") is False
    assert coerce.as_bool("TRUE") is True
    assert coerce.as_bool(1) is True
    assert coerce.as_bool(0) is False


def test_as_bool_rejects_string_truthiness():
    # The reviewed bug: the string "false" is TRUTHY in Python. as_bool must reject
    # unknown strings, never coerce them to True.
    for bad in ("", "maybe", "2", "yes please", "null", "None"):
        with pytest.raises(CoercionError):
            coerce.as_bool(bad)


def test_as_bool_rejects_none():
    with pytest.raises(CoercionError):
        coerce.as_bool(None)
    assert coerce.opt_bool(None) is None
    assert coerce.opt_bool("true") is True


def test_as_float_rejects_none_and_nonfinite():
    assert coerce.as_float("860.0") == 860.0
    assert coerce.as_float("1e3") == 1000.0
    with pytest.raises(CoercionError):
        coerce.as_float(None)
    with pytest.raises(CoercionError):
        coerce.as_float("nan")
    with pytest.raises(CoercionError):
        coerce.as_float("inf")
    with pytest.raises(CoercionError):
        coerce.as_float("not-a-number")
    # bool must not slip through as 1.0/0.0
    with pytest.raises(CoercionError):
        coerce.as_float(True)


def test_as_float_allow_nonfinite_optin():
    assert math.isnan(coerce.as_float("nan", allow_nonfinite=True))


def test_opt_float_null_ok_nonfinite_still_rejected():
    assert coerce.opt_float(None) is None
    assert coerce.opt_float("3.5") == 3.5
    with pytest.raises(CoercionError):
        coerce.opt_float("inf")


def test_as_int_strict():
    assert coerce.as_int("5") == 5
    assert coerce.as_int("5.0") == 5
    with pytest.raises(CoercionError):
        coerce.as_int("5.5")
    with pytest.raises(CoercionError):
        coerce.as_int(None)


def test_as_str_rejects_none():
    assert coerce.as_str("x") == "x"
    assert coerce.as_str(3) == "3"
    with pytest.raises(CoercionError):
        coerce.as_str(None)


def test_require_missing_key():
    with pytest.raises(CoercionError):
        coerce.require({"a": 1}, "b")
    assert coerce.require({"a": 1}, "a") == 1
