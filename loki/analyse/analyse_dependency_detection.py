# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from loki import Loop, SubstituteExpressions, SubstituteExpressionsMapper, LoopRange, IntLiteral, Transformer
from loki import FindNodes, Loop, Cast, simplify


___all___ = ['normalize_bounds']

def normalize_bounds(start_node, routine):
    loops = [node for node in FindNodes(Loop).visit(start_node)]

    transformer_map = {}
    for loop_node in loops:
        loop_variable = loop_node.variable
        bounds = loop_node.bounds
        (a,b,c) = (bounds.start, bounds.stop, bounds.step)

        if c is None:
            c = IntLiteral(1)
        if a==c==1:
            continue #do nothing if already normalized
            
        loop_variable_map = {loop_variable : (loop_variable - 1) * c + a}
        loop_bounds_map = {bounds : LoopRange((IntLiteral(1), Cast("INT",(b-a)/c + 1), IntLiteral(1)))}
    
        mapped_bounds = SubstituteExpressionsMapper(loop_bounds_map)(loop_node.bounds)
        new_body = SubstituteExpressions(loop_variable_map).visit(loop_node.body)
        transformer_map[loop_node] = loop_node.clone(bounds=mapped_bounds, body=new_body)
    return Transformer(transformer_map).visit(routine.body)