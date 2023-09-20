# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from loki import (
    Loop,
    SubstituteExpressions,
    SubstituteExpressionsMapper,
    LoopRange,
    IntLiteral,
    Transformer,
    FindNodes,
)

___all___ = ["normalize_bounds"]


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


def _get_nested_loops(loop):
    """
    Helper routine to yield all loops in a loop nest.
    """
    yield loop
    yield from _implementation_get_nested_loops(loop)


def normalize_bounds(start_node):
    loops_greedy = [node for node in FindNodes(Loop, greedy=True).visit(start_node)]

    transformer_map = {}
    for loop_start in loops_greedy:
        nested_loops = list(_get_nested_loops(loop_start))

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
                loop_variable_map = {loop_variable: (loop_variable - 1) * c + a}
                loop_bounds_map = {
                    bounds: LoopRange((IntLiteral(1), (b - a) / c + 1, IntLiteral(1)))
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
