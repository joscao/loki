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


__all___ = ["add", "sub", "mul", "binary_operation"]


def _get_bounds(x, y):
    return (x.start, x.stop, y.start, y.stop)


def binary_operation(op, x, y):
    """
    Apply binary operation `op` to intervals `x` and `y`. Assuming that the binary operation is defined for all `x`, `y`.
    """
    x_1, x_2, y_1, y_2 = _get_bounds(x, y)

    tmp = (op(x_1, y_1), op(x_1, y_2), op(x_2, y_1), op(x_2, y_2))
    start = min(tmp)
    stop = max(tmp)

    return x.__class__((start, stop))


def add(x, y):
    x_1, x_2, y_1, y_2 = _get_bounds(x, y)

    start = x_1 + y_1
    stop = x_2 + y_2

    return x.__class__((start, stop))


def sub(x, y):
    x_1, x_2, y_1, y_2 = _get_bounds(x, y)

    start = x_1 - y_2
    stop = x_2 - y_1

    return x.__class__((start, stop))


def mul(x, y):
    x_1, x_2, y_1, y_2 = _get_bounds(x, y)

    start = min(x_1 * y_1, x_1 * y_2, x_2 * y_1, x_2 * y_2)
    stop = max(x_1 * y_1, x_1 * y_2, x_2 * y_1, x_2 * y_2)

    return x.__class__((start, stop))
