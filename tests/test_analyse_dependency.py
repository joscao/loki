# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import warnings
from pathlib import Path
from shutil import rmtree
import numpy as np
import pytest
from conftest import jit_compile
from sympy import Matrix as sympy_matrix, sympify, Implies, And
from loki import (
    Sourcefile,
    Loop,
    FindNodes,
    IntLiteral,
    parse_fparser_expression,
    Scope,
)
from loki.analyse.analyse_dependency_detection import (
    normalize_bounds,
    construct_affine_array_access_function_representation,
)

from loki.analyse.analyse_dependency_detection import get_nested_loops
from loki.analyse.util_polyhedron import Polyhedron


@pytest.fixture(scope="module", name="here")
def fixture_here():
    return Path(__file__).parent


def is_normalized(node):
    assert isinstance(node, Loop)
    bounds = node.bounds
    (a, _, c) = (bounds.start, bounds.stop, bounds.step)

    if c is None:
        c = IntLiteral(1)
    return a == c == 1


base_path = "sources/data_dependency_detection/"
build_path = "build/data_dependency_detection/"


def test_bounds_normalization(here, test_file="bounds_normalization.f90"):
    rmtree(Path(here / build_path))
    Path(here / build_path).mkdir(parents=True, exist_ok=True)

    original_filepath = here / base_path / test_file

    routine = Sourcefile.from_file(original_filepath)
    filepath = here / build_path / test_file.replace(".f90", "original_tmp.f90")

    function = jit_compile(
        routine, filepath=filepath, objname="boundsnormalizationtests"
    )

    n = 46
    expected = np.zeros(shape=(n,), order="F", dtype=np.int32)
    function(n, expected)

    subroutine = routine.subroutines[0]
    subroutine.body = normalize_bounds(subroutine.body)

    loops = FindNodes(Loop).visit(subroutine.body)
    for loop in loops:
        assert is_normalized(loop)

    filepath = here / build_path / test_file.replace(".f90", "normalized_tmp.f90")

    function = jit_compile(
        routine, filepath=filepath, objname="boundsnormalizationtests"
    )

    actual = np.zeros(shape=(n,), order="F", dtype=np.int32)
    function(n, actual)

    assert np.array_equal(expected, actual)


different_value_initalization_functions = [
    lambda dim1, dim2, dim3: np.ones(shape=(dim1, dim2, dim3), order="F"),
    lambda dim1, dim2, dim3: np.zeros(shape=(dim1, dim2, dim3), order="F"),
    np.random.rand,
]


@pytest.mark.parametrize(
    "initialization_function", different_value_initalization_functions
)
def test_nested_loops_calculation(
    here, initialization_function, test_file="bounds_normalization.f90"
):
    rmtree(Path(here / build_path))
    Path(here / build_path).mkdir(parents=True, exist_ok=True)

    original_filepath = here / base_path / test_file

    routine = Sourcefile.from_file(original_filepath)
    filepath = here / build_path / test_file.replace(".f90", "original_tmp.f90")

    function = jit_compile(
        routine, filepath=filepath, objname="nested_loops_calculation"
    )

    (dim1, dim2, dim3) = (10, 13, 12)
    input_array = initialization_function(dim1, dim2, dim3)
    expected = function(input_array, dim1, dim2, dim3)

    subroutine = routine["nested_loops_calculation"]
    subroutine.body = normalize_bounds(subroutine.body)

    loops = FindNodes(Loop).visit(subroutine.body)
    for loop in loops:
        assert is_normalized(loop)

    filepath = here / build_path / test_file.replace(".f90", "normalized_tmp.f90")

    function = jit_compile(
        routine, filepath=filepath, objname="nested_loops_calculation"
    )
    actual = function(input_array, dim1, dim2, dim3)

    assert expected == actual


@pytest.mark.parametrize(
    "array_dimensions_expr, expected",
    [
        ("i-1", ([[1, 0]], [[-1]])),
        ("i,j", ([[1, 0], [0, 1]], [[0], [0]])),
        ("j,j+1", ([[0, 1], [0, 1]], [[0], [1]])),
        ("1,2", ([[0, 0], [0, 0]], [[1], [2]])),
        ("1,i,2*i+j", ([[0, 0], [1, 0], [2, 1]], [[1], [0], [0]])),
    ],
)
def test_access_function_creation(array_dimensions_expr, expected):
    scope = Scope()
    first = parse_fparser_expression(f"z({array_dimensions_expr})", scope)

    use_these_variables = ["i", "j"]

    F, f, variables = construct_affine_array_access_function_representation(
        first.dimensions, use_these_variables
    )

    assert np.array_equal(F, np.array(expected[0], dtype=np.dtype(int)))
    assert np.array_equal(f, np.array(expected[1], dtype=np.dtype(int)))
    assert np.array_equal(variables, np.array(["i", "j"], dtype=np.dtype(object)))


src_path = "sources/data_dependency_detection/"


def yield_routine(here, filename, subroutine_names):
    source = Sourcefile.from_file(here / src_path / filename)

    for name in subroutine_names:
        yield source[name]


@pytest.mark.parametrize(
    "filename, subroutine_names",
    [
        (
            "loop_carried_dependencies.f90",
            [
                "SimpleDependency",
                "NestedDependency",
                "ConditionalDependency",
                "NoDependency",
            ],
        ),
        (
            "various_loops.f90",
            [
                "single_loop",
                "single_loop_split_access",
                "single_loop_arithmetic_operations_for_access",
                "nested_loop_single_dimensions_access",
                "nested_loop_partially_used",
                "partially_used_array",
            ],
        ),
        (
            "bounds_normalization.f90",
            ["boundsnormalizationtests", "nested_loops_calculation"],
        ),
    ],
)
def test_correct_iteration_space_extraction(here, filename, subroutine_names):
    """
    Test if the iteration space is correctly extracted from the loop bounds, by comparing the inequalities gained
    with the loop bounds by symbolic evaluation, performed by sympy. An additional assumption is made, that inside
    the loop body the loop bounds are not violated, this should almost always hold, but is not checked.
    """
    for routine in yield_routine(here, filename, subroutine_names):
        nested_loops = list(get_nested_loops(routine.body))
        loop_variables = [loop.variable for loop in nested_loops]
        loop_ranges = [loop.bounds for loop in nested_loops]

        try:
            poly = Polyhedron.from_nested_loops(nested_loops)
        except (ValueError, AssertionError) as e:
            warnings.warn(str(e), UserWarning)
            continue  # skip if the polyhedron cannot be constructed

        B, b = poly.get_B_b_representation()
        iteration_space_required_variables = list(str(v) for v in poly.variables)

        B = sympy_matrix(B)
        b = sympy_matrix(b)
        v = sympy_matrix(iteration_space_required_variables)

        inequality_rhs = B * v + b

        # if the loop body is entered the start of the loop range must be smaller equal than the stop of the loop range
        implied_loop_conditions = [
            sympify(str(range.stop) + ">=" + str(range.start)) for range in loop_ranges
        ]

        expr_with_lower_bound = inequality_rhs.subs(
            {str(v): str(range.start) for v, range in zip(loop_variables, loop_ranges)}
        )
        expr_with_upper_bound = inequality_rhs.subs(
            {str(v): str(range.stop) for v, range in zip(loop_variables, loop_ranges)}
        )

        for expr in expr_with_lower_bound:
            assert Implies(And(*implied_loop_conditions), expr >= 0)

        for expr in expr_with_upper_bound:
            assert Implies(And(*implied_loop_conditions), expr >= 0)
