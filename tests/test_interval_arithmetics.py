# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import pytest

from loki import RangeIndex
from loki.expression.interval_arithmetics import add, mul, sub, binary_operation


@pytest.mark.parametrize(
    "x, y, result",
    [
        ((1, 2), (5, 7), (6, 9)),
        ((-2, 2), (3, 3), (1, 5)),  # Adding intervals with negative numbers
        ((0, 0), (0, 0), (0, 0)),  # Adding intervals with zeros
        ((-1, 1), (1, 3), (0, 4)),  # Resulting interval containing zero
        ((-5, -3), (-2, -1), (-7, -4)),  # Negative intervals
    ],
)
def test_add(x, y, result):
    assert add(RangeIndex(x), RangeIndex(y)) == RangeIndex(result)
    assert binary_operation(
        lambda a, b: a + b, RangeIndex(x), RangeIndex(y)
    ) == RangeIndex(result)


@pytest.mark.parametrize(
    "x, y, result",
    [
        ((1, 2), (5, 7), (-6, -3)),
        ((-2, 2), (3, 3), (-5, -1)),  # Subtracting intervals with negative numbers
        ((0, 0), (0, 0), (0, 0)),  # Subtracting intervals with zeros
        ((-1, 1), (1, 3), (-4, 0)),  # Resulting interval containing zero
        ((-5, -3), (-2, -1), (-4, -1)),  # Negative intervals
    ],
)
def test_sub(x, y, result):
    assert sub(RangeIndex(x), RangeIndex(y)) == RangeIndex(result)
    assert binary_operation(
        lambda a, b: a - b, RangeIndex(x), RangeIndex(y)
    ) == RangeIndex(result)


@pytest.mark.parametrize(
    "x, y, result",
    [
        ((1, 2), (5, 7), (5, 14)),
        ((-2, 2), (3, 3), (-6, 6)),  # Multiplying intervals with negative numbers
        ((0, 0), (0, 0), (0, 0)),  # Multiplying intervals with zeros
        ((-1, 1), (1, 3), (-3, 3)),  # Resulting interval containing zero
        ((-5, -3), (-2, -1), (3, 10)),  # Negative intervals
    ],
)
def test_mul(x, y, result):
    assert mul(RangeIndex(x), RangeIndex(y)) == RangeIndex(result)
    assert binary_operation(
        lambda a, b: a * b, RangeIndex(x), RangeIndex(y)
    ) == RangeIndex(result)


@pytest.mark.parametrize(
    "op, x, y, result",
    [
        (lambda a, b: a + b, (1, 2), (3, 4), (4, 6)),  # Addition
        (lambda a, b: a - b, (5, 7), (2, 3), (2, 5)),  # Subtraction
        (lambda a, b: a * b, (-2, 2), (3, 3), (-6, 6)),  # Multiplication
        (
            lambda a, b: a / b,
            (4, 8),
            (2, 2),
            (2.0, 4.0),
        ),  # Division with casting to float
        (
            lambda a, b: a // b,
            (3, 8),
            (2, 2),
            (1, 4),
        ),  # Division with explicit integer division
        (lambda a, b: a**b, (2, 3), (2, 3), (4, 27)),  # Exponentiation
        (max, (1, 2), (3, 4), (3, 4)),  # Maximum
        (min, (5, 7), (2, 3), (2, 3)),  # Minimum
    ],
)
def test_binary_operation(op, x, y, result):
    assert binary_operation(op, RangeIndex(x), RangeIndex(y)) == RangeIndex(result)


# Test for a custom binary operation
def custom_operation(a, b):
    return a * 2 + b * 3


@pytest.mark.parametrize(
    "x, y, result",
    [
        ((1, 2), (3, 4), (11, 16)),
        ((-2, 2), (3, 3), (5, 13)),
    ],
)
def test_custom_binary_operation(x, y, result):
    assert binary_operation(
        custom_operation, RangeIndex(x), RangeIndex(y)
    ) == RangeIndex(result)


# test scalar cases
@pytest.mark.parametrize(
    "operation, optional_custom_op, input_x, input_y, expected_result",
    [
        (add, None, RangeIndex((1, 3)), 2, RangeIndex((3, 5))),
        (add, None, 2, RangeIndex((1, 3)), RangeIndex((3, 5))),
        (sub, None, RangeIndex((1, 3)), 2, RangeIndex((-1, 1))),
        (sub, None, 2, RangeIndex((1, 3)), RangeIndex((-1, 1))),
        (mul, None, RangeIndex((1, 3)), 2, RangeIndex((2, 6))),
        (mul, None, 2, RangeIndex((1, 3)), RangeIndex((2, 6))),
        (
            binary_operation,
            lambda x, y: x * y,
            RangeIndex((1, 3)),
            2,
            RangeIndex((2, 6)),
        ),
        (
            binary_operation,
            lambda x, y: x * y,
            2,
            RangeIndex((1, 3)),
            RangeIndex((2, 6)),
        ),
    ],
)
def test_operations_on_scalar_and_range_index(
    operation, optional_custom_op, input_x, input_y, expected_result
):
    if optional_custom_op is None:
        result = operation(input_x, input_y)
    else:
        result = operation(optional_custom_op, input_x, input_y)
    assert result == expected_result
