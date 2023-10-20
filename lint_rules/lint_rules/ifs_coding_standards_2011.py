# (C) Copyright 2018- ECMWF.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

# pylint: disable=invalid-all-format
"""
Implementation of rules in the IFS coding standards document (2011) for loki-lint.
"""

from pathlib import Path
import re

from pymbolic.primitives import Expression

from loki import (
    Visitor,
    FindNodes,
    ExpressionFinder,
    ExpressionRetriever,
    flatten,
    as_tuple,
    strip_inline_comments,
    Module,
    Subroutine,
    BasicType,
    ir,
)
from loki.lint import GenericRule, RuleType
from loki.expression import symbols as sym


class CodeBodyRule(GenericRule):  # Coding standards 1.3

    type = RuleType.WARN

    docs = {
        "id": "1.3",
        "title": (
            "Rules for Code Body: "
            "Nesting of conditional blocks should not be more than {max_nesting_depth} "
            "levels deep;"
        ),
    }

    config = {
        "max_nesting_depth": 3,
    }

    class NestingDepthVisitor(Visitor):
        @classmethod
        def default_retval(cls):
            return []

        def __init__(self, max_nesting_depth):
            super().__init__()
            self.max_nesting_depth = max_nesting_depth

        def visit(self, o, *args, **kwargs):
            return flatten(super().visit(o, *args, **kwargs))

        def visit_Conditional(self, o, **kwargs):
            level = kwargs.pop("level", 0)
            too_deep = []
            if level >= self.max_nesting_depth and not getattr(o, "inline", False):
                too_deep = [o]
            too_deep += self.visit(o.body, level=level + 1, **kwargs)
            if o.has_elseif:
                too_deep += self.visit(o.else_body, level=level, **kwargs)
            else:
                too_deep += self.visit(o.else_body, level=level + 1, **kwargs)
            return too_deep

        def visit_MultiConditional(self, o, **kwargs):
            level = kwargs.pop("level", 0)
            too_deep = []
            if level >= self.max_nesting_depth and not getattr(o, "inline", False):
                too_deep = [o]
            too_deep += self.visit(o.bodies, level=level + 1, **kwargs)
            too_deep += self.visit(o.else_body, level=level + 1, **kwargs)
            return too_deep

    @classmethod
    def check_subroutine(cls, subroutine, rule_report, config, **kwargs):
        """Check the code body: Nesting of conditional blocks."""
        too_deep = cls.NestingDepthVisitor(config["max_nesting_depth"]).visit(
            subroutine.body
        )
        msg = f'Nesting of conditionals exceeds limit of {config["max_nesting_depth"]}'
        for node in too_deep:
            rule_report.add(msg, node)


class ModuleNamingRule(GenericRule):  # Coding standards 1.5

    type = RuleType.WARN

    docs = {
        "id": "1.5",
        "title": (
            'Naming Schemes for Modules: All modules should end with "_mod". '
            "Module filename should match the name of the module it contains."
        ),
    }

    @classmethod
    def check_module(cls, module, rule_report, config):
        """Check the module name and the name of the source file."""
        if not module.name.lower().endswith("_mod"):
            msg = f'Name of module "{module.name}" should end with "_mod"'
            rule_report.add(msg, module)

        if module.source.file:
            path = Path(module.source.file)
            if module.name.lower() != path.stem.lower():
                msg = f'Module filename "{path.name}" does not match module name "{module.name}"'
                rule_report.add(msg, module)


class DrHookRule(GenericRule):  # Coding standards 1.9

    type = RuleType.SERIOUS

    docs = {
        "id": "1.9",
        "title": "Rules for DR_HOOK",
    }

    non_exec_nodes = (ir.Comment, ir.CommentBlock, ir.Pragma, ir.PreprocessorDirective)

    @classmethod
    def _find_lhook_conditional(cls, ast, is_reversed=False):
        cond = None
        for node in reversed(ast) if is_reversed else ast:
            if isinstance(node, ir.Conditional):
                if node.condition == "LHOOK":
                    cond = node
                    break
            elif not isinstance(node, cls.non_exec_nodes):
                # Break if executable statement encountered
                break
        return cond

    @classmethod
    def _find_lhook_call(cls, cond, is_reversed=False):
        call = None
        if cond:
            # We use as_tuple here because the conditional can be inline and then its body is not
            # iterable but a single node (e.g., CallStatement)
            body = reversed(as_tuple(cond.body)) if is_reversed else as_tuple(cond.body)
            for node in body:
                if isinstance(node, ir.CallStatement) and node.name == "DR_HOOK":
                    call = node
                elif not isinstance(node, cls.non_exec_nodes):
                    # Break if executable statement encountered
                    break
        return call

    @staticmethod
    def _get_string_argument(scope):
        string_arg = scope.name.upper()
        while hasattr(scope, "parent") and scope.parent:
            scope = scope.parent
            if isinstance(scope, Subroutine):
                string_arg = scope.name.upper() + "%" + string_arg
            elif isinstance(scope, Module):
                string_arg = scope.name.upper() + ":" + string_arg
        return string_arg

    @classmethod
    def _check_lhook_call(cls, call, subroutine, rule_report, pos="First"):
        if call is None:
            msg = f"{pos} executable statement must be call to DR_HOOK"
            rule_report.add(msg, subroutine)
        elif call.arguments:
            string_arg = cls._get_string_argument(subroutine)
            if (
                not isinstance(call.arguments[0], sym.StringLiteral)
                or call.arguments[0].value.upper() != string_arg
            ):
                msg = f'String argument to DR_HOOK call should be "{string_arg}"'
                rule_report.add(msg, call)
            second_arg = {"First": "0", "Last": "1"}
            if not (
                len(call.arguments) > 1
                and isinstance(call.arguments[1], sym.IntLiteral)
                and str(call.arguments[1].value) == second_arg[pos]
            ):
                msg = f'Second argument to DR_HOOK call should be "{second_arg[pos]}"'
                rule_report.add(msg, call)
            if not (len(call.arguments) > 2 and call.arguments[2] == "ZHOOK_HANDLE"):
                msg = 'Third argument to DR_HOOK call should be "ZHOOK_HANDLE".'
                rule_report.add(msg, call)

    @classmethod
    def check_subroutine(cls, subroutine, rule_report, config, **kwargs):
        """Check that first and last executable statements in the subroutine
        are conditionals with calls to DR_HOOK in their body and that the
        correct arguments are given to the call."""
        # Extract the AST for the subroutine body
        ast = subroutine.body
        if isinstance(ast, ir.Section):
            ast = ast.body
        ast = flatten(ast)

        # Look for conditionals in subroutine body
        first_cond = cls._find_lhook_conditional(ast)
        last_cond = cls._find_lhook_conditional(ast, is_reversed=True)

        # Find calls to DR_HOOK
        first_call = cls._find_lhook_call(first_cond)
        last_call = cls._find_lhook_call(last_cond, is_reversed=True)

        cls._check_lhook_call(first_call, subroutine, rule_report)
        cls._check_lhook_call(last_call, subroutine, rule_report, pos="Last")


class LimitSubroutineStatementsRule(GenericRule):  # Coding standards 2.2

    type = RuleType.WARN

    docs = {
        "id": "2.2",
        "title": "Subroutines should have no more than {max_num_statements} executable statements.",
    }

    config = {"max_num_statements": 300}

    # List of nodes that are considered executable statements
    exec_nodes = (
        ir.Assignment,
        ir.MaskedStatement,
        ir.Intrinsic,
        ir.Allocation,
        ir.Deallocation,
        ir.Nullify,
        ir.CallStatement,
    )

    # Pattern for intrinsic nodes that are allowed as non-executable statements
    match_non_exec_intrinsic_node = re.compile(r"\s*(?:PRINT|FORMAT)", re.I)

    @classmethod
    def check_subroutine(cls, subroutine, rule_report, config, **kwargs):
        """Count the number of nodes in the subroutine and check if they exceed
        a given maximum number.
        """
        # Count total number of executable nodes
        nodes = FindNodes(cls.exec_nodes).visit(subroutine.ir)
        num_nodes = len(nodes)
        # Subtract number of non-exec intrinsic nodes
        intrinsic_nodes = filter(lambda node: isinstance(node, ir.Intrinsic), nodes)
        num_nodes -= sum(
            1
            for _ in filter(
                lambda node: cls.match_non_exec_intrinsic_node.match(node.text),
                intrinsic_nodes,
            )
        )

        if num_nodes > config["max_num_statements"]:
            msg = (
                f"Subroutine has {num_nodes} executable statements "
                f'(should not have more than {config["max_num_statements"]})'
            )
            rule_report.add(msg, subroutine)


class MaxDummyArgsRule(GenericRule):  # Coding standards 3.6

    type = RuleType.INFO

    docs = {
        "id": "3.6",
        "title": "Routines should have no more than {max_num_arguments} dummy arguments.",
    }

    config = {"max_num_arguments": 50}

    @classmethod
    def check_subroutine(cls, subroutine, rule_report, config, **kwargs):
        """
        Count the number of dummy arguments and report if given
        maximum number exceeded.
        """
        num_arguments = len(subroutine.arguments)
        if num_arguments > config["max_num_arguments"]:
            msg = (
                f"Subroutine has {num_arguments} dummy arguments "
                f'(should not have more than {config["max_num_arguments"]})'
            )
            rule_report.add(msg, subroutine)


class MplCdstringRule(GenericRule):  # Coding standards 3.12

    type = RuleType.SERIOUS

    docs = {
        "id": "3.12",
        "title": 'Calls to MPL subroutines should provide a "CDSTRING" identifying the caller.',
    }

    @classmethod
    def check_subroutine(cls, subroutine, rule_report, config, **kwargs):
        """Check all calls to MPL subroutines for a CDSTRING."""
        for call in FindNodes(ir.CallStatement).visit(subroutine.ir):
            if str(call.name).upper().startswith("MPL_"):
                for kw, _ in call.kwarguments:
                    if kw.upper() == "CDSTRING":
                        break
                else:
                    msg = f'No "CDSTRING" provided in call to {call.name}'
                    rule_report.add(msg, call)


class ImplicitNoneRule(GenericRule):  # Coding standards 4.4

    type = RuleType.SERIOUS

    docs = {
        "id": "4.4",
        "title": '"IMPLICIT NONE" is mandatory in all routines.',
    }

    _regex = re.compile(r"implicit\s+none\b", re.I)

    @staticmethod
    def check_for_implicit_none(ast):
        """
        Check for intrinsic nodes that match the regex.
        """
        for intr in FindNodes(ir.Intrinsic).visit(ast):
            if ImplicitNoneRule._regex.match(intr.text):
                break
        else:
            return False
        return True

    @classmethod
    def check_subroutine(cls, subroutine, rule_report, config, **kwargs):
        """
        Check for IMPLICIT NONE in the subroutine's spec or any enclosing
        scope.
        """
        found_implicit_none = cls.check_for_implicit_none(subroutine.ir)

        # Check if enclosing scopes contain implicit none
        scope = subroutine.parent
        while scope and not found_implicit_none:
            if hasattr(scope, "spec") and scope.spec:
                found_implicit_none = cls.check_for_implicit_none(scope.spec)
            scope = scope.parent if hasattr(scope, "parent") else None

        if not found_implicit_none:
            # No 'IMPLICIT NONE' intrinsic node was found
            rule_report.add('No "IMPLICIT NONE" found', subroutine)


class ExplicitKindRule(GenericRule):  # Coding standards 4.7

    type = RuleType.SERIOUS

    docs = {
        "id": "4.7",
        "title": (
            "Variables and constants must be declared with explicit kind, using the kinds "
            'defined in "PARKIND1" and "PARKIND2".'
        ),
    }

    config = {
        "declaration_types": ["INTEGER", "REAL"],
        "constant_types": ["REAL"],  # Coding standards document includes INTEGERS here
        "allowed_type_kinds": {
            "INTEGER": ["JPIM", "JPIT", "JPIB", "JPIA", "JPIS", "JPIH"],
            "REAL": ["JPRB", "JPRM", "JPRS", "JPRT", "JPRH", "JPRD", "JPHOOK"],
        },
    }

    @staticmethod
    def check_kind_declarations(subroutine, types, allowed_type_kinds, rule_report):
        """Helper function that carries out the check for explicit kind specification
        on all declarations.
        """
        for decl in FindNodes(ir.VariableDeclaration).visit(subroutine.spec):
            decl_type = decl.symbols[0].type
            if decl_type.dtype in types:
                if not decl_type.kind:
                    # Declared without any KIND specification
                    msg = f'{", ".join(str(var) for var in decl.symbols)} without explicit KIND declared'
                    rule_report.add(msg, decl)
                elif allowed_type_kinds.get(decl_type.dtype):
                    if decl_type.kind not in allowed_type_kinds[decl_type.dtype]:
                        # We have a KIND but it does not match any of the allowed kinds
                        msg = (
                            f"{decl_type.kind!s} is not an allowed KIND value for "
                            f'{", ".join(str(var) for var in decl.symbols)}'
                        )
                        rule_report.add(msg, decl)

    @staticmethod
    def check_kind_literals(subroutine, types, allowed_type_kinds, rule_report):
        """Helper function that carries out the check for explicit kind specification
        on all literals.
        """

        class FindLiteralsWithKind(ExpressionFinder):
            """
            Custom expression finder that that yields all literals of the types
            specified in the config and stops recursion on loop ranges and array subscripts
            (to avoid warnings about integer constants in these cases)
            """

            retriever = ExpressionRetriever(
                query=lambda e: isinstance(e, types),
                recurse_query=lambda e: not isinstance(e, (sym.Array, sym.Range)),
            )

        for node, exprs in FindLiteralsWithKind(unique=False, with_ir_node=True).visit(
            subroutine.ir
        ):
            for literal in exprs:
                if not literal.kind:
                    rule_report.add(f"{literal} used without explicit KIND", node)
                elif allowed_type_kinds.get(literal.__class__):
                    if (
                        str(literal.kind).upper()
                        not in allowed_type_kinds[literal.__class__]
                    ):
                        msg = (
                            f"{literal.kind} is not an allowed KIND value for {literal}"
                        )
                        rule_report.add(msg, node)

    @classmethod
    def check_subroutine(cls, subroutine, rule_report, config, **kwargs):
        """Check for explicit kind information in constants and
        variable declarations.
        """
        # 1. Check variable declarations for explicit KIND
        #
        # When we check variable type information, we have BasicType values to identify
        # whether a variable is REAL, INTEGER, ... Therefore, we create a map that uses
        # the corresponding BasicType values as keys to look up allowed kinds for each type.
        # Since the case does not matter, we convert all allowed type kinds to upper case.
        types = tuple(BasicType.from_str(name) for name in config["declaration_types"])
        allowed_type_kinds = {}
        if config.get("allowed_type_kinds"):
            allowed_type_kinds = {
                BasicType.from_str(name): [kind.upper() for kind in kinds]
                for name, kinds in config["allowed_type_kinds"].items()
            }

        cls.check_kind_declarations(subroutine, types, allowed_type_kinds, rule_report)

        # 2. Check constants for explicit KIND
        #
        # Constants are represented by an instance of some Literal class, which directly
        # gives us their type. Therefore, we create a map that uses the corresponding
        # Literal types as keys to look up allowed kinds for each type. Again, we
        # convert all allowed type kinds to upper case.
        type_map = {
            "INTEGER": sym.IntLiteral,
            "REAL": sym.FloatLiteral,
            "LOGICAL": sym.LogicLiteral,
            "CHARACTER": sym.StringLiteral,
        }
        types = tuple(type_map[name] for name in config["constant_types"])
        if config.get("allowed_type_kinds"):
            allowed_type_kinds = {
                type_map[name]: [kind.upper() for kind in kinds]
                for name, kinds in config["allowed_type_kinds"].items()
            }

        cls.check_kind_literals(subroutine, types, allowed_type_kinds, rule_report)


class BannedStatementsRule(GenericRule):  # Coding standards 4.11

    type = RuleType.WARN

    docs = {
        "id": "4.11",
        "title": "Banned statements.",
    }

    config = {
        "banned": [
            "STOP",
            "PRINT",
            "RETURN",
            "ENTRY",
            "DIMENSION",
            "DOUBLE PRECISION",
            "COMPLEX",
            "GO TO",
            "CONTINUE",
            "FORMAT",
            "COMMON",
            "EQUIVALENCE",
        ],
    }

    @classmethod
    def check_subroutine(cls, subroutine, rule_report, config, **kwargs):
        """Check for banned statements in intrinsic nodes."""
        for intr in FindNodes(ir.Intrinsic).visit(subroutine.ir):
            for keyword in config["banned"]:
                if keyword.lower() in intr.text.lower():
                    rule_report.add(f'Banned keyword "{keyword}"', intr)


class Fortran90OperatorsRule(GenericRule):  # Coding standards 4.15

    type = RuleType.WARN

    docs = {"id": "4.15", "title": "Use Fortran 90 comparison operators."}

    fixable = True

    """
    Regex patterns for each operator that match F77 and F90 operators as
    named groups, thus allowing to easily find out which operator was used.
    """
    _op_patterns = {
        "==": re.compile(r"(?P<f77>\.eq\.)|(?P<f90>==)", re.I),
        "!=": re.compile(r"(?P<f77>\.ne\.)|(?P<f90>/=)", re.I),
        ">=": re.compile(r"(?P<f77>\.ge\.)|(?P<f90>>=)", re.I),
        "<=": re.compile(r"(?P<f77>\.le\.)|(?P<f90><=)", re.I),
        ">": re.compile(r"(?P<f77>\.gt\.)|(?P<f90>>(?!=))", re.I),
        "<": re.compile(r"(?P<f77>\.lt\.)|(?P<f90><(?!=))", re.I),
    }

    _op_map = {
        "==": ".eq.",
        "/=": ".ne.",
        ">=": ".ge.",
        "<=": ".le.",
        ">": ".gt.",
        "<": ".lt.",
    }

    class ComparisonRetriever(Visitor):
        """
        Bespoke expression retriever that extracts 3-tuples containing
        ``(node, expression root, comparison)`` for all :any:`Comparison` nodes.
        """

        retriever = ExpressionRetriever(lambda e: isinstance(e, sym.Comparison))

        def visit_Node(self, o, **kwargs):
            """
            Generic visitor method that will call the :any:`ExpressionRetriever`
            only on :class:`pymbolic.primitives.Expression` children, collecting
            ``(node, expression root, comparison)`` tuples for all matches.
            """
            retval = ()
            for ch in flatten(o.children):
                if isinstance(ch, Expression):
                    comparisons = self.retriever.retrieve(ch)
                    if comparisons:
                        retval += ((o, ch, comparisons),)
                elif ch is not None:
                    retval += self.visit(ch, **kwargs)
            return retval

        def visit_tuple(self, o, **kwargs):
            """
            Specialized handling of tuples to concatenate the nested tuples
            returned by :meth:`visit_Node`.
            """
            retval = ()
            for ch in o:
                if ch is not None:
                    retval += self.visit(ch, **kwargs)
            return retval

        visit_list = visit_tuple

    @classmethod
    def check_subroutine(cls, subroutine, rule_report, config, **kwargs):
        """Check for the use of Fortran 90 comparison operators."""
        # Use the bespoke visitor to retrieve all comparison nodes alongside with their expression root
        # and the IR node they belong to
        for node, expr_root, expr_list in cls.ComparisonRetriever().visit(
            subroutine.ir
        ):
            # Use the string representation of the expression to find the source line
            lstart, lend = node.source.find(str(expr_root))
            lines = node.source.clone_lines((lstart, lend))

            # For each comparison operator, use the original source code (because the frontends always
            # translate them to F90 operators) to check if F90 or F77 operators were used
            for op in sorted({op.operator for op in expr_list}):
                # find source line for operator
                op_str = op if op != "!=" else "/="
                line = [
                    line
                    for line in lines
                    if op_str in strip_inline_comments(line.string)
                ]
                if not line:
                    line = [
                        line
                        for line in lines
                        if op_str
                        in strip_inline_comments(
                            line.string.replace(cls._op_map[op_str], op_str)
                        )
                    ]

                source_string = strip_inline_comments(line[0].string)
                matches = cls._op_patterns[op].findall(source_string)
                for f77, _ in matches:
                    if f77:
                        msg = f'Use Fortran 90 comparison operator "{op_str}" instead of "{f77}"'
                        rule_report.add(msg, node)

    @classmethod
    def fix_subroutine(cls, subroutine, rule_report, config):
        """Replace by Fortran 90 comparison operators."""
        # We only have to invalidate the source string for the expression. This will cause the
        # backend to regenerate the source string for that node and use Fortran 90 operators
        # automatically
        mapper = {}
        for report in rule_report.problem_reports:
            new_expr = report.location
            new_expr.update_metadata({"source": None})
            mapper[report.location] = new_expr
        return mapper


# Create the __all__ property of the module to contain only the rule names
__all__ = tuple(
    name for name in dir() if name.endswith("Rule") and name != "GenericRule"
)
