SUBROUTINE BoundsNormalizationTests(array_size, output)
  use iso_fortran_env
  implicit none
  integer, intent(in) :: array_size
  INTEGER, intent(inout) :: output(array_size)
  INTEGER, PARAMETER :: const_start = 1, const_end = 10, const_step = 1
  INTEGER :: i, start, stop, result
  INTEGER :: running_index = 1
  
  ! Test 1: Normalized bounds
  start = 1
  stop = 10
  DO i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  END DO
  
  ! Test 2: Bounds reversed
  start = 10
  stop = 1
  DO i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  END DO
  
  ! Test 3: Bounds equal
  start = 5
  stop = 5
  DO i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  END DO

  ! Test 4: Negative bounds
  start = -5
  stop = 5
  DO i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  END DO

  ! Test 5: Bounds in reverse order
  start = 5
  stop = -5
  DO i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  END DO

  ! Test 6: Lower bound is larger than upper bound
  start = 7
  stop = 3
  DO i=start,stop,-1
    output(running_index) = i
    running_index = running_index + 1
  END DO

  ! Test 7: Both bounds are zero
  start = 0
  stop = 0
  DO i=start,stop
    output(running_index) = i
    running_index = running_index + 1
  END DO

  ! Test 8: Bounds with fractional values
  start = 2.5
  stop = 8.7
  DO i=INT(start),INT(stop)
    output(running_index) = i
    running_index = running_index + 1
  END DO

  ! Test 9: Bounds with large step
  start = 1
  stop = 10
  DO i=start,stop,5
    output(running_index) = i
    running_index = running_index + 1
  END DO

  ! Test 10: Constants normalized
  DO i=const_start,const_end,const_step
    output(running_index) = i
    running_index = running_index + 1
  END DO

  
END SUBROUTINE BoundsNormalizationTests