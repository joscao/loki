module loopmodule
  implicit none

  public :: loopa, loopb, loopc

contains

  ! subroutine to implement loop a
  subroutine loopa(x)
    real, dimension(:,:), intent(inout) :: x
    integer :: i

    do i = 10, 49, 7
      x(i, i+1) = 0.0
    end do

  end subroutine loopa

  ! subroutine to implement loop b
  subroutine loopb(x)
    real, dimension(:), intent(inout) :: x
    integer :: i,j 

    do i = -3, 10, 2
      do j = 1, 10, 2
      x(4+i+j) = x(3+i+1+j)
      end do
    end do

  end subroutine loopb

  ! subroutine to implement loop c
  subroutine loopc(x)
    real, dimension(:), intent(inout) :: x
    integer :: i

    do i = 50, 10, -1
      x(i) = 0.0 
    end do

  end subroutine loopc

  subroutine calculatenonsense(arr, dim1, dim2, dim3, result)
    integer, intent(in) :: dim1, dim2, dim3
    real, dimension(dim1, dim2, dim3), intent(in) :: arr
    real, intent(out) :: result
    integer :: i, j, k

    result = 0.0  ! initialize the result to 0.0

    do i = 5, dim1
      do j = 6, dim2
        do k = 2, dim3
          result = result + arr(i, j, k)
        end do

        DO k = 1, dim3
          result = result + arr(i, j, k)
        END DO
      end do

      DO k = 1, dim3
        result = result + arr(i, j, k)
      END DO

    end do
  end subroutine calculatenonsense

end module loopmodule