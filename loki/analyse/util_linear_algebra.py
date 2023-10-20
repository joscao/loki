# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from math import gcd
from numpy import zeros_like, dot
from numpy import vstack, hstack, logical_and
from numpy import all as np_all, sum as np_sum, empty as np_empty, unique as np_unique

__all__ = [
    "back_substitution",
    "generate_reduced_row_echelon_form",
    "NoIntegerSolution",
    "row_echelon_form_under_gcd_condition",
    "is_independent_system",
    "yield_one_d_systems",
    "bounds_of_one_d_system",
]


def is_independent_system(matrix):
    """
    Check if a linear system of equations can be split into independent one-dimensional problems.

    Args:
        matrix (numpy.ndarray): A rectangular matrix representing coefficients.

    Returns:
        bool: True if the system can be split into independent one-dimensional problems, False otherwise.

    This function checks whether a linear system of equations in the form of matrix x [operator] right_hand_side
    can be split into independent one-dimensional problems. The number of problems is determined by the
    number of variables (the row number of the matrix).

    Each problem consists of a coefficient vector and a right-hand side. The system can be considered independent
    if each row of the matrix has exactly one non-zero coefficient.
    """

    return np_all(np_sum(matrix != 0, axis=1) == 1)


def yield_one_d_systems(matrix, right_hand_side, drop_zero_rows=True):
    """
    Split a linear system of equations into independent one-dimensional problems.

    Args:
        matrix (numpy.ndarray): A rectangular matrix representing coefficients.
        right_hand_side (numpy.ndarray): The right-hand side vector.
        drop_zero_rows (bool, optional): If True, drop rows where both coefficients and right-hand side are zero.

    Yields:
        tuple: A tuple containing a one-column coefficient matrix and the corresponding right-hand side.

    This function takes a linear system of equations in the form of matrix x [operator] right_hand_side,
    where "matrix" is a rectangular matrix, x is a vector of variables, and "right_hand_side" is
    the right-hand side vector. It splits the system into independent one-dimensional problems.

    Each problem consists of a coefficient vector and a right-hand side. The number of problems is equal to the
    number of variables (the row number of the matrix).

    You can choose to drop rows where both the coefficients and the right-hand side are zero by setting
    the drop_zero_rows parameter to True.

    Note:
    - The independence of the problems is not explicitly checked.

    Example:
    ```
    for A, b in yield_one_d_systems(matrix, right_hand_side):
        # Solve the one-dimensional problem A * x = b
        solution = solve_one_d_system(A, b)
    ```
    """
    for A, b in zip(matrix.T, right_hand_side.T):
        if drop_zero_rows:
            mask = ~np_all(hstack((A, b)) == 0)
            yield A[mask].T, b[mask].T
        else:
            yield A.T, b.T


def bounds_of_one_d_system(single_column_matrix, right_hand_side):
    """
    Calculate the lower and upper bounds of a one-dimensional linear inequality
    represented by the equation: single_column_matrix * x >= right_hand_side.

    Args:
        single_column_matrix (numpy.ndarray): A single-column matrix representing coefficients.
        right_hand_side (numpy.ndarray): The right-hand side vector.

    Returns:
        tuple: A tuple containing the lower and upper bounds for variable x that satisfy the inequality.
    """
    mask = single_column_matrix >= 0
    zero_mask = single_column_matrix == 0
    lower_bounds = np_empty(zero_mask[mask].size, dtype=right_hand_side.dtype)
    valid_divsion_mask = logical_and(mask,~zero_mask)
    count = right_hand_side[valid_divsion_mask].reshape(-1).size
    lower_bounds[0:count] = right_hand_side[valid_divsion_mask] / single_column_matrix[valid_divsion_mask]

    lower_bounds[count:] = right_hand_side[logical_and(mask, zero_mask)]

    upper_bounds = right_hand_side[~mask] / single_column_matrix[~mask]

    return np_unique(lower_bounds), np_unique(upper_bounds)


def back_substitution(
    upper_triangular_square_matrix,
    right_hand_side,
    divison_operation=lambda x, y: x / y,
):
    """
    Solve a linear system of equations using back substitution for an upper triangular square matrix.

    Args:
        upper_triangular_square_matrix (numpy.ndarray): An upper triangular square matrix (R).
        right_hand_side (numpy.ndarray): A vector (y) on the right-hand side of the equation Rx = y.
        division_operation (function, optional): A custom division operation function. Default is standard division (/).

    Returns:
        numpy.ndarray: The solution vector (x) to the system of equations Rx = y.

    The function performs back substitution to find the solution vector x for the equation Rx = y,
    where R is an upper triangular square matrix and y is a vector. The division_operation
    function is used for division (e.g., for custom division operations).

    Note:
    - The function assumes that the upper right element of the upper_triangular_square_matrix (R)
      is nonzero for proper back substitution.
    """
    R = upper_triangular_square_matrix
    y = right_hand_side

    x = zeros_like(y)

    assert R[-1, -1] != 0

    x[-1] = divison_operation(y[-1], R[-1, -1])

    for i in range(len(y) - 2, -1, -1):
        x[i] = divison_operation((y[i] - dot(R[i, i + 1 :], x[i + 1 :])), R[i, i])

    return x


def generate_reduced_row_echelon_form(
    A, conditional_check=lambda: None, division_operator=lambda x, y: x / y
):
    """
    Calculate the Reduced Row Echelon Form (RREF) of a matrix A using Gaussian elimination.

    Args:
        A (numpy.ndarray): The input matrix for which RREF is to be calculated.
        conditional_check (function, optional): A custom function to check conditions during the computation.
        division_operation (function, optional): A custom division operation function. Default is standard division (/).

    Returns:
        numpy.ndarray: The RREF of the input matrix A.

    This function computes the Reduced Row Echelon Form (RREF) of a given matrix A using Gaussian elimination.
    You can provide a custom conditional_check function to add checks or operations during the computation.
    You can also specify a custom division_operation function for division (e.g., for custom division operations).

    Note:
    - If the input matrix has no rows or columns, it is already in RREF, and the function returns itself.
    - The function utilizes the specified division operation (default is standard division) for division.

    Reference: https://math.stackexchange.com/questions/3073083/how-to-reduce-matrix-into-row-echelon-form-in-numpy
    """
    # if matrix A has no columns or rows,
    # it is already in REF, so we return itself
    r, c = A.shape
    if r == 0 or c == 0:
        return A

    # we search for non-zero element in the first column
    for i in range(len(A)):
        if A[i, 0] != 0:
            break
    else:
        # if all elements in the first column is zero,
        # we perform REF on matrix from second column
        B = row_echelon_form_under_gcd_condition(A[:, 1:])
        # and then add the first zero-column back
        return hstack([A[:, :1], B])

    # if non-zero element happens not in the first row,
    # we switch rows
    if i > 0:
        A[[i, 0]] = A[[0, i]]

    # check condition
    conditional_check(A)

    # we divide first row by first element in it
    A[0] = division_operator(A[0], A[0, 0])
    # we subtract all subsequent rows with first row (it has 1 now as first element)
    # multiplied by the corresponding element in the first column
    A[1:] -= A[0] * A[1:, 0:1]

    # we perform REF on matrix from second row, from second column
    B = row_echelon_form_under_gcd_condition(A[1:, 1:])

    # we add first row and first (zero) column, and return
    return vstack([A[:1], hstack([A[1:, :1], B])])


class NoIntegerSolution(Exception):
    pass


def row_echelon_form_under_gcd_condition(A):
    """
    Return the Row Echelon Form (REF) of an integer matrix A while ensuring integer solutions
    to linear Diophantine equations.

    Args:
        A (numpy.ndarray): The input integer matrix.

    Returns:
        numpy.ndarray: The REF of the input matrix A under the GCD (Greatest Common Divisor) condition.

    This function computes the Row Echelon Form (REF) of a given integer matrix A while enforcing that
    each linear Diophantine equation in the system has integer solutions. It follows Theorem 11.32
    in "Compilers: Principles, Techniques, and Tools" by Aho, Lam, Sethi, and Ullman (2015).
    """

    def gcd_condition(A):
        """Check that gcd condition of linear Diophantine equation is satisfied"""
        if A[0, -1] % gcd(*A[0, :-1]) != 0:
            raise NoIntegerSolution()

    return generate_reduced_row_echelon_form(
        A, conditional_check=gcd_condition, division_operator=lambda x, y: x // y
    )
