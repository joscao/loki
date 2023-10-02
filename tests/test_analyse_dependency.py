# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
from shutil import rmtree
import numpy as np
import pytest
from conftest import jit_compile
from loki import (
    Sourcefile,
    Loop,
    FindNodes,
    IntLiteral,
    parse_fparser_expression,
    FindVariables,
    Scope,
)
from loki.analyse.analyse_dependency_detection import (
    normalize_bounds,
    construct_affine_array_access_function_representation,
)


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


def test_boundsnormalization(here, test_file="bounds_normalization.f90"):
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


# test the detection of the affine array access function


@pytest.mark.parametrize(
        "array_dimensions_expr, expected", [
            ("i-1", ([[1,0]],[[-1]])),
            ("i,j", ([[1,0],[0,1]],[[0],[0]])),
            ("j,j+1",([[0,1],[0,1]],[[0],[1]])),
            ("1,2",([[0,0],[0,0]],[[1],[2]])),
            ("1,i,2*i+j",([[0,0],[1,0],[2,1]],[[1],[0],[0]])),
        ]
)
def test_access_function_creation(array_dimensions_expr, expected):
    scope = Scope()
    first = parse_fparser_expression(f"z({array_dimensions_expr})", scope)
    make_all_variables_available = parse_fparser_expression("z(i,j)", scope)

    variables = FindVariables().visit(
        (*first.dimensions, *make_all_variables_available.dimensions)
    )

    F, f, variables = construct_affine_array_access_function_representation(first.dimensions, variables)

    assert np.array_equal(F, np.array(expected[0],dtype=np.dtype(int)))
    assert np.array_equal(f, np.array(expected[1],dtype=np.dtype(int)))
    assert np.array_equal(variables, np.array(["i","j"],dtype=np.dtype(object)))
