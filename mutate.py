"""Deterministic flaw generator: one AST mutation per site.

Each mutant records what was changed, so for these candidates the *intended*
change is known. Whether that change produces an *observable* defect is a
separate question, answered by the audit (equivalent mutants exist).
"""
import ast
import copy

CMP_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
            ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is}


class _Sites(ast.NodeVisitor):
    def __init__(self):
        self.sites = []

    def generic_visit(self, node):
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                if type(op) in CMP_SWAP:
                    self.sites.append(("boundary_or_comparison", node, i))
        elif isinstance(node, ast.Constant) and type(node.value) is int:
            self.sites.append(("off_by_one_constant", node, None))
        elif isinstance(node, ast.BoolOp):
            self.sites.append(("and_or_swap", node, None))
        elif isinstance(node, ast.If):
            self.sites.append(("dropped_branch", node, None))
        elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Attribute):
            self.sites.append(("dropped_pointer_update", node, None))
        elif isinstance(node, ast.Attribute) and node.attr in ("next", "left", "right") \
                and isinstance(node.ctx, ast.Load):
            self.sites.append(("wrong_pointer", node, None))
        super().generic_visit(node)


def _apply(tree, target_index, kind, op_index):
    """Return a mutated copy of tree, mutating the target_index-th site."""
    tree = copy.deepcopy(tree)
    finder = _Sites(); finder.visit(tree)
    _, node, _ = finder.sites[target_index]
    if kind == "boundary_or_comparison":
        node.ops[op_index] = CMP_SWAP[type(node.ops[op_index])]()
        return tree, f"comparison changed to {type(node.ops[op_index]).__name__}"
    if kind == "off_by_one_constant":
        node.value = node.value + 1
        return tree, f"constant changed to {node.value}"
    if kind == "and_or_swap":
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
        return tree, "and/or swapped"
    if kind == "dropped_branch":
        node.body = [ast.Pass()]
        return tree, f"body of if at line {node.lineno} removed"
    if kind == "dropped_pointer_update":
        parent_body = None
        for p in ast.walk(tree):
            for field in ("body", "orelse"):
                b = getattr(p, field, None)
                if isinstance(b, list) and node in b:
                    parent_body = b
        parent_body[parent_body.index(node)] = ast.Pass()
        return tree, f"pointer update at line {node.lineno} removed"
    if kind == "wrong_pointer":
        node.attr = {"next": "next", "left": "right", "right": "left"}[node.attr] \
            if node.attr != "next" else "next"
        if node.attr == "next":
            # .next -> .next.next is the classic slow/fast pointer slip
            node.value = ast.Attribute(value=node.value, attr="next", ctx=ast.Load())
        return tree, f"pointer changed at line {node.lineno}"
    raise ValueError(kind)


def mutants(source):
    tree = ast.parse(source)
    finder = _Sites(); finder.visit(tree)
    out = []
    for i, (kind, _, op_index) in enumerate(finder.sites):
        try:
            mt, desc = _apply(tree, i, kind, op_index)
            ast.fix_missing_locations(mt)
            code = ast.unparse(mt)
        except Exception:
            continue
        if code.strip() != ast.unparse(tree).strip():
            out.append(dict(intended_flaw=kind, change=desc, code=code))
    return out
