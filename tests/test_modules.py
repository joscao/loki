from pathlib import Path
import pytest

from loki import OFP, OMNI, FP, Module, Declaration, TypeDef, fexprgen, DataType


@pytest.mark.parametrize('frontend', [FP, OFP, OMNI])
def test_module_from_source(frontend):
    """
    Test the creation of `Module` objects from raw source strings.
    """
    fcode = """
module a_module
  integer, parameter :: x = 2
  integer, parameter :: y = 3

  type derived_type
    real :: array(x, y)
  end type derived_type
contains

  subroutine my_routine(pt)
    type(derived_type) :: pt
    pt%array(:,:) = 42.0
  end subroutine my_routine
end module a_module
"""
    module = Module.from_source(fcode, frontend=frontend)
    assert len([o for o in module.spec.body if isinstance(o, Declaration)]) == 2
    assert len([o for o in module.spec.body if isinstance(o, TypeDef)]) == 1
    assert 'derived_type' in module.typedefs
    assert len(module.routines) == 1
    assert module.routines[0].name == 'my_routine'


@pytest.mark.parametrize('frontend', [
    FP,
    pytest.param(OFP, marks=pytest.mark.xfail(reason='Typedefs not yet supported in frontend')),
    OMNI
])
def test_module_external_typedefs(frontend):
    """
    Test that externally provided type information is correctly
    attached to `Module` components when supplied via the `typedefs`
    parameter in the constructor.
    """
    fcode_external = """
module external_mod
  integer, parameter :: x = 2
  integer, parameter :: y = 3

  type ext_type
    real :: array(x, y)
  end type ext_type
end module external_mod
"""

    fcode_module = """
module a_module
  use external_mod, only: ext_type
  implicit none

  type nested_type
    type(ext_type) :: ext
  end type nested_type
contains

  subroutine my_routine(pt)
    type(nested_type) :: pt
    pt%ext%array(:,:) = 42.0
  end subroutine my_routine
end module a_module
"""

    external = Module.from_source(fcode_external, frontend=frontend)
    assert'ext_type' in external.typedefs

    module = Module.from_source(fcode_module, frontend=frontend,
                                typedefs=external.typedefs)
    nested = module.typedefs['nested_type']
    ext = nested.variables[0]

    # OMNI resolves explicit shape parameters in the frontend parser
    exptected_array_shape = '(1:2, 1:3)' if frontend == OMNI else '(x, y)'

    # Check that the `array` variable in the `ext` type is found and
    # has correct type and shape info
    assert 'array' in ext.type.variables
    a = ext.type.variables['array']
    assert a.type.dtype == DataType.REAL
    fexprgen(a.shape) == exptected_array_shape

    # Check the routine has got type and shape info too
    routine = module['my_routine']
    pt = routine.variables[0]
    pt_ext = pt.type.variables['ext']
    assert 'array' in pt_ext.type.variables
    pt_ext_a = pt_ext.type.variables['array']
    assert pt_ext_a.type.dtype == DataType.REAL
    fexprgen(pt_ext_a.shape) == exptected_array_shape

    # Check the LHS of the assignment has correct meta-data
    pt_ext_arr = routine.body[0].target
    assert pt_ext_arr.type.dtype == DataType.REAL
    fexprgen(pt_ext_arr.shape) == exptected_array_shape
