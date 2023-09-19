module LoopModule
  implicit none

  public :: LoopA, LoopB, LoopC

contains

  ! Subroutine to implement Loop A
  subroutine LoopA(X)
    real, dimension(:,:), intent(inout) :: X
    integer :: i

    do i = 10, 49, 7
      X(i, i+1) = 0.0
    end do

  end subroutine LoopA

  ! Subroutine to implement Loop B
  subroutine LoopB(X)
    real, dimension(:), intent(inout) :: X
    integer :: i

    do i = -3, 10, 2
      X(4+i) = X(3+i+1)
    end do

  end subroutine LoopB

  ! Subroutine to implement Loop C
  subroutine LoopC(X)
    real, dimension(:), intent(inout) :: X
    integer :: i

    do i = 50, 10, -1
      X(i) = 0.0 
    end do

  end subroutine LoopC

end module LoopModule