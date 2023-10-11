subroutine single_loop(arr, n)
  implicit none
  integer, intent(inout) :: arr(:)
  integer, intent(in) :: n
  integer :: i

  do i = 1, n
    arr(i) = arr(i) * 2
  end do
end subroutine single_loop

subroutine single_loop_split_access(arr, n)
  implicit none
  integer, intent(inout) :: arr(:)
  integer, intent(in) :: n
  integer :: i

  do i = 1, n/2
    arr(2*i) = arr(2*i) * 2
    arr(2*i + 1) = arr(2*i + 1) * 2
  end do
end subroutine single_loop_split_access

subroutine single_loop_arithmetic_operations_for_access(arr, n)
  implicit none
  integer, intent(inout) :: arr(:)
  integer, intent(in) :: n
  integer :: i

  do i = 1, n
    arr(i*i) = arr(i + i) * 2
  end do
end subroutine single_loop_arithmetic_operations_for_access

subroutine nested_loop_single_dimensions_access(arr, n)
  implicit none
  integer, intent(inout) :: arr(:)
  integer, intent(in) :: n
  integer :: i, j

  do i = 1, n/2
    do j = 1, n/2
          arr(i + j) = arr(i + j) * 2
    end do
  end do
end subroutine nested_loop_single_dimensions_access



subroutine nested_loop_partially_used(arr, n)
  implicit none
  integer, intent(inout) :: arr(:)
  integer, intent(in) :: n
  integer :: i, j

  do i = 1, n/4
    do j = 1, n/4
          arr(i + j) = arr(i + j) * 2
    end do
  end do
end subroutine nested_loop_partially_used


subroutine partially_used_array(arr, n)
  implicit none
  integer, intent(out) :: arr(:)
  integer, intent(in) :: n
  integer :: i = 1 , j = 3

  arr(1) = 1
  do i = 2, n/2
    arr(i) = arr(i - 1)
  end do

  j = arr(j)
end subroutine partially_used_array