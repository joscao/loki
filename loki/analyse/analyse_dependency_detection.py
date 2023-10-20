# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import numpy as np
from loki import (
    Loop,
    SubstituteExpressions,
    SubstituteExpressionsMapper,
    LoopRange,
    IntLiteral,
    Transformer,
    FindNodes,
    simplify,
    FindVariables,
    Simplification,
    is_constant,
    accumulate_polynomial_terms,
)
from loki.expression import symbols as sym

___all___ = [
    "normalize_bounds",
    "get_nested_loops",
    "construct_affine_array_access_function_representation",
]


def construct_affine_array_access_function_representation(
    array_dimensions_expr: tuple(), additional_variables: list[str] = None
):
    """
    Construct a matrix, vector representation of the access function of an array.
    E.g. z[i], where the expression ("i", ) should be passed to this function,
         y[1+3,4-j], where ("1+3", "4-j") should be passed to this function,
         if var=Array(...), then var.dimensions should be passed to this function.
    Returns: matrix, vector: F,f mapping a vecector i within the bounds Bi+b>=0 to the
    array location Fi+f
    """

    def generate_row(expr, variables):
        supported_types = (sym.TypedSymbol, sym.MetaSymbol, sym.Sum, sym.Product)
        if not (is_constant(expr) or isinstance(expr, supported_types)):
            raise ValueError(f"Cannot derive inequality from expr {str(expr)}")
        simplified_expr = simplify(expr)
        terms = accumulate_polynomial_terms(simplified_expr)
        const_term = terms.pop(1, 0)  # Constant term or 0
        row = np.zeros(len(variables), dtype=np.dtype(int))

        for base, coef in terms.items():
            if not len(base) == 1:
                raise ValueError(f"Non-affine bound {str(simplified_expr)}")
            row[variables.index(base[0].name.lower())] = coef

        return row, const_term

    def unique_order_preserving(sequence):
        seen = set()
        return [x for x in sequence if not (x in seen or seen.add(x))]

    if additional_variables is None:
        additional_variables = list()

    for variable in additional_variables:
        assert variable.lower() == variable

    variables = additional_variables.copy()
    variables += list({v.name.lower() for v in FindVariables().visit(array_dimensions_expr)})
    variables = unique_order_preserving(variables)

    n = len(array_dimensions_expr)
    d = len(variables)

    F = np.zeros([n, d], dtype=np.dtype(int))
    f = np.zeros([n, 1], dtype=np.dtype(int))

    for dimension_index, sub_expr in enumerate(array_dimensions_expr):
        row, constant = generate_row(sub_expr, variables)
        F[dimension_index] = row
        f[dimension_index, 0] = constant
    return F, f, variables


def _implementation_get_nested_loops(loop):
    """
    Implementation of obtaining nested loops.
    """
    loops = []
    for node in loop.body:
        if isinstance(node, Loop):
            loops.append(node)
            yield node
    for node in loops:
        yield from _implementation_get_nested_loops(node)


def get_nested_loops(loop):
    """
    Helper routine to yield all loops in a loop nest.
    """
    if isinstance(loop, Loop):
        yield loop
    yield from _implementation_get_nested_loops(loop)


def _simplify(expression):
    return simplify(
        expression,
        enabled_simplifications=Simplification.IntegerArithmetic
        | Simplification.CollectCoefficients
        # until flatting is fixed for proper integer divison (issue #155)
    )


def normalize_bounds(start_node):
    loops_greedy = [node for node in FindNodes(Loop, greedy=True).visit(start_node)]

    transformer_map = {}
    for loop_start in loops_greedy:
        nested_loops = list(get_nested_loops(loop_start))

        mapped_bounds, new_body, new_node = None, None, {}
        for loop_node in reversed(nested_loops):
            loop_variable = loop_node.variable
            bounds = loop_node.bounds
            (a, b, c) = (bounds.start, bounds.stop, bounds.step)

            if c is None:
                c = IntLiteral(1)

            loop_variable_map = {}
            loop_bounds_map = {}

            if not a == c == 1:
                loop_variable_map = {
                    loop_variable: _simplify((loop_variable - 1) * c + a)
                }

                try:
                    upper_bound = (b.value - a.value) // c.value + 1
                except AttributeError:
                    upper_bound = _simplify((b - a) / c + 1)

                loop_bounds_map = {
                    bounds: LoopRange((IntLiteral(1), upper_bound, IntLiteral(1)))
                }

            mapped_bounds = SubstituteExpressionsMapper(loop_bounds_map)(
                loop_node.bounds
            )

            copy_body = tuple(
                new_node.get(element, element) for element in loop_node.body
            )

            new_body = SubstituteExpressions(loop_variable_map).visit(copy_body)

            new_node[loop_node] = loop_node.clone(bounds=mapped_bounds, body=new_body)

        if mapped_bounds is not None and new_body is not None:
            transformer_map[loop_start] = loop_start.clone(
                bounds=mapped_bounds, body=new_body
            )
    return Transformer(transformer_map).visit(start_node)
