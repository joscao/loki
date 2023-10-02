# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""
Collection of arithmetic operations on intervals/ranges --> made with RangeIndex in mind
WARNING: Step size for ranges is disregarded in all operations, only valid upper and lower bounds are created!
https://en.wikipedia.org/wiki/Interval_arithmetic
"""

from loki.expression.symbols import RangeIndex

__all___ = ["add", "sub", "mul", "binary_operation", "unary_operation"]


def _get_bounds(x, y):
    return (x.start, x.stop, y.start, y.stop)


def _binary_operation_on_range_index(op, x: RangeIndex, y: RangeIndex):
    x_1, x_2, y_1, y_2 = _get_bounds(x, y)
    tmp = (op(x_1, y_1), op(x_1, y_2), op(x_2, y_1), op(x_2, y_2))

    return RangeIndex((min(tmp), max(tmp)))


# both cases necessary since operation might not be symnetric
def _binary_operation_on_range_index_and_scalar(op, x: RangeIndex, y):
    x_1, x_2 = x.start, x.stop
    tmp = (op(x_1, y), op(x_2, y))

    return RangeIndex((min(tmp), max(tmp)))


def _binary_operation_on_scalar_and_range_index(op, x, y: RangeIndex):
    y_1, y_2 = y.start, y.stop
    tmp = (op(x, y_1), op(x, y_2))

    return RangeIndex((min(tmp), max(tmp)))


def binary_operation(op, x, y):
    """
    Apply binary operation `op` to intervals `x` and `y`. Assuming
    that the binary operation is well defined.
    """
    if x.__class__ == y.__class__ == RangeIndex:
        return _binary_operation_on_range_index(op, x, y)

    if x.__class__ is not RangeIndex:
        return _binary_operation_on_scalar_and_range_index(op, x, y)

    if y.__class__ is not RangeIndex:
        return _binary_operation_on_range_index_and_scalar(op, x, y)


def unary_operation(op, x : RangeIndex):
    """
    Apply unary operation `op` to interval `x`. Assuming
    that the unary operation is well defined.
    """
    return RangeIndex((op(x.start), op(x.stop)))


def _add_on_range_index(x: RangeIndex, y: RangeIndex):
    x_1, x_2, y_1, y_2 = _get_bounds(x, y)

    return RangeIndex((x_1 + y_1, x_2 + y_2))


# single case sufficient since addition is symmetric
def _add_on_range_index_and_scalar(x: RangeIndex, y):
    x_1, x_2 = x.start, x.stop

    return RangeIndex((x_1 + y, x_2 + y))


def add(x, y):
    if x.__class__ == y.__class__ == RangeIndex:
        return _add_on_range_index(x, y)

    if x.__class__ is not RangeIndex:
        return _add_on_range_index_and_scalar(x=y, y=x)
    if y.__class__ is not RangeIndex:
        return _add_on_range_index_and_scalar(x, y)


def _sub_on_range_index(x: RangeIndex, y: RangeIndex):
    x_1, x_2, y_1, y_2 = _get_bounds(x, y)

    return RangeIndex((x_1 - y_2, x_2 - y_1))


def _sub_on_range_index_and_scalar(x: RangeIndex, y):
    x_1, x_2 = x.start, x.stop

    return RangeIndex((x_1 - y, x_2 - y))


def _sub_on_scalar_and_range_index(x, y: RangeIndex):
    y_1, y_2 = y.start, y.stop

    return RangeIndex((x - y_2, x - y_1))


def sub(x, y):
    if x.__class__ == y.__class__ == RangeIndex:
        return _sub_on_range_index(x, y)

    if x.__class__ is not RangeIndex:
        return _sub_on_scalar_and_range_index(x, y)
    if y.__class__ is not RangeIndex:
        return _sub_on_range_index_and_scalar(x, y)


def _mul_on_range_index(x: RangeIndex, y: RangeIndex):
    x_1, x_2, y_1, y_2 = _get_bounds(x, y)

    tmp = (x_1 * y_1, x_1 * y_2, x_2 * y_1, x_2 * y_2)

    return RangeIndex((min(tmp), max(tmp)))


# multiplication is symmetric
def _mul_on_range_index_and_scalar(x: RangeIndex, y):
    x_1, x_2 = x.start, x.stop

    tmp = (x_1 * y, x_2 * y)

    return RangeIndex((min(tmp), max(tmp)))


def mul(x, y):
    if x.__class__ == y.__class__ == RangeIndex:
        return _mul_on_range_index(x, y)

    if x.__class__ is not RangeIndex:
        return _mul_on_range_index_and_scalar(x=y, y=x)
    if y.__class__ is not RangeIndex:
        return _mul_on_range_index_and_scalar(x, y)
