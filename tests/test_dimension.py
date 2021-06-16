import pytest

from loki import OFP, OMNI, FP, Subroutine, Dimension, FindNodes, Loop


@pytest.mark.parametrize('frontend', [FP, OFP, OMNI])
def test_dimension_size(frontend):
    """
    Test that ``Dimension`` objects match size expressions.
    """
    fcode = """
subroutine test_dimension_size(nlon, start, end, arr)
  integer, intent(in) :: NLON, START, END
  real, intent(inout) :: arr(nlon)
  real :: local_arr(1:nlon)
  real :: range_arr(end-start+1)

  arr(start:end) = 1.
end subroutine test_dimension_size
"""
    routine = Subroutine.from_source(fcode, frontend=frontend)

    # Create the dimension object and make sure we match all array sizes
    dim = Dimension(name='test_dim', size='nlon', bounds=('start', 'end'))
    assert routine.variable_map['nlon'] == dim.size
    assert routine.variable_map['arr'].dimensions.index_tuple[0] == dim.size

    # Ensure that aliased size expressions laos trigger right
    assert routine.variable_map['nlon'] in dim.size_expressions
    assert routine.variable_map['local_arr'].dimensions.index_tuple[0] in dim.size_expressions
    assert routine.variable_map['range_arr'].dimensions.index_tuple[0] in dim.size_expressions


@pytest.mark.parametrize('frontend', [FP, OFP, OMNI])
def test_dimension_index_range(frontend):
    """
    Test that ``Dimension`` objects match index and range expressions.
    """
    fcode = """
subroutine test_dimension_index(nlon, start, end, arr)
  integer, intent(in) :: NLON, START, END
  real, intent(inout) :: arr(nlon)
  integer :: I

  do i=start, end
    arr(I) = 1.
  end do
end subroutine test_dimension_index
"""
    routine = Subroutine.from_source(fcode, frontend=frontend)

    # Create the dimension object and make sure we match all array sizes
    dim = Dimension(name='test_dim', index='i', bounds=('start', 'end'))
    assert routine.variable_map['i'] == dim.index

    assert FindNodes(Loop).visit(routine.body)[0].bounds == dim.range
    assert FindNodes(Loop).visit(routine.body)[0].bounds.lower == dim.bounds[0]
    assert FindNodes(Loop).visit(routine.body)[0].bounds.upper == dim.bounds[1]