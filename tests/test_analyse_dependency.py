# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from pathlib import Path
import numpy as np
import pytest
from conftest import jit_compile
from loki import Sourcefile
from loki.analyse.analyse_dependency_detection import normalize_bounds

@pytest.fixture(scope="module", name="here")
def fixture_here():
    return Path(__file__).parent

base_path = "sources/data_dependency_detection/"
test_files = ["bounds_normalization.f90"]

@pytest.mark.parametrize("test_file", test_files)
def test_fortran_output_consistency(here, test_file):
    original_filepath = here / base_path / test_file
    

    routine = Sourcefile.from_file(original_filepath)
    filepath = here / "build/" / test_file.replace(".f90", "original_tmp.f90")
    
    function = jit_compile(
        routine, filepath=filepath, objname="boundsnormalizationtests"
    )

    n = 46
    expected = np.zeros(shape=(n,), order='F', dtype=np.int32)
    function(n, expected)

    subroutine = routine.subroutines[0]
    subroutine.body = normalize_bounds(subroutine.body, subroutine)

    filepath = here / "build/" / test_file.replace(".f90", "normalized_tmp.f90")

    function = jit_compile(
        routine, filepath=filepath, objname="boundsnormalizationtests"
    )

    actual = np.zeros(shape=(n,), order='F', dtype=np.int32)
    function(n, actual)

    assert np.array_equal(expected,actual)
