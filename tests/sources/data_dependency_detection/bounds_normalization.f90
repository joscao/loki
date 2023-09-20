subroutine boundsnormalizationtests(array_size, output)
  use iso_fortran_env
  implicit none
  integer, intent(in) :: array_size
  integer, intent(inout) :: output(array_size)
  integer, parameter :: const_start = 1, const_end = 10, const_step = 1
  integer :: i, start, stop
  integer :: running_index = 1
  
  ! test 1: normalized bounds
  start = 1
  stop = 10
  do i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  end do
  
  ! test 2: bounds reversed
  start = 10
  stop = 1
  do i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  end do
  
  ! test 3: bounds equal
  start = 5
  stop = 5
  do i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  end do

  ! test 4: negative bounds
  start = -5
  stop = 5
  do i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  end do

  ! test 5: bounds in reverse order
  start = 5
  stop = -5
  do i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  end do

  ! test 6: lower bound is larger than upper bound
  start = 7
  stop = 3
  do i=start,stop,-1
    output(running_index) = i
    running_index = running_index + 1
  end do

  ! test 7: both bounds are zero
  start = 0
  stop = 0
  do i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  end do

  ! test 8: bounds with large step
  start = 1
  stop = 10
  do i=start,stop, 5
    output(running_index) = i
    running_index = running_index + 1
  end do

  ! test 9: constants normalized
  do i=const_start,const_end,const_step
    output(running_index) = i
    running_index = running_index + 1
  end do
end subroutine boundsnormalizationtests

subroutine nested_loops_calculation(result, arr, dim1, dim2, dim3)
  use iso_fortran_env, only: real64
  integer, intent(in) :: dim1, dim2, dim3
  real, intent(in) :: arr(dim1, dim2, dim3)
  real, intent(out) :: result
  integer :: i, j, k

  result = 0.0

  do k = 1, dim3
    do j = 6, dim2
      do i = 5, dim1
        result = result + arr(i, j, k)
      end do
    end do
  end do

  do j = 6, dim2
    do k = 1, dim3
      do i = 5, dim1
        result = result + arr(i, j, k)
      end do
    end do
  end do

  do j = 6, dim2
    do k = 1, dim3
      do i = 5, dim1
        result = result + arr(i, j, k)
      end do
    end do
  end do
end subroutine nested_loops_calculation