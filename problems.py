"""SC1007-style data structures problems used by the audit.

Each problem has:
  - a reference solution (source text, so it can be mutated),
  - course_tests: a few hand-written cases, the kind a lab autograder ships with,
  - adversarial_inputs(): edge cases plus randomised inputs, checked by
    differential testing against the reference.

All problems are standard public exercises (LeetCode 704, 876, 206, 98, 102).
"""
import random
from collections import deque


class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def build_list(vals):
    head = None
    for v in reversed(vals):
        head = ListNode(v, head)
    return head


def list_vals(head, limit=10_000):
    out = []
    while head is not None and len(out) < limit:
        out.append(head.val)
        head = head.next
    return out


def build_tree(level):
    """Build a tree from a LeetCode-style level-order list with None gaps."""
    if not level or level[0] is None:
        return None
    root = TreeNode(level[0])
    q, i = deque([root]), 1
    while q and i < len(level):
        node = q.popleft()
        if i < len(level) and level[i] is not None:
            node.left = TreeNode(level[i]); q.append(node.left)
        i += 1
        if i < len(level) and level[i] is not None:
            node.right = TreeNode(level[i]); q.append(node.right)
        i += 1
    return root


def random_bst_level(rng, n, valid=True):
    vals = rng.sample(range(-50, 50), n)
    root = None

    def insert(node, v):
        if node is None:
            return TreeNode(v)
        if v < node.val:
            node.left = insert(node.left, v)
        else:
            node.right = insert(node.right, v)
        return node

    for v in vals:
        root = insert(root, v)
    if not valid and n >= 3:
        # break the BST property somewhere deep, not only at the root's children
        nodes, q = [], deque([root])
        while q:
            x = q.popleft(); nodes.append(x)
            q.extend(c for c in (x.left, x.right) if c)
        rng.choice(nodes[1:]).val = rng.choice([root.val, root.val + 1, -60, 60])
    # serialise to level order
    out, q = [], deque([root])
    while q:
        x = q.popleft()
        if x is None:
            out.append(None); continue
        out.append(x.val); q.append(x.left); q.append(x.right)
    while out and out[-1] is None:
        out.pop()
    return out


PROBLEMS = {}


def problem(name, entry, reference, course_tests, adversarial, run):
    PROBLEMS[name] = dict(name=name, entry=entry, reference=reference,
                          course_tests=course_tests, adversarial=adversarial, run=run)


# ---------------------------------------------------------------- binary search
problem(
    "binary_search", "search",
    reference='''
def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
''',
    course_tests=[(([-1, 0, 3, 5, 9, 12], 9),), (([-1, 0, 3, 5, 9, 12], 2),), (([5], 5),)],
    adversarial=lambda rng: (
        [(([], 1),), (([5], 4),), (([1, 3], 3),), (([1, 3], 1),), (([1, 3], 0),), (([1, 3], 4),)]
        + [((sorted(rng.sample(range(-100, 100), k)), rng.randint(-110, 110)),)
           for k in [rng.randint(0, 20) for _ in range(300)]]
    ),
    run=lambda f, args: f(list(args[0]), args[1]),
)

# ------------------------------------------------------ middle of a linked list
problem(
    "middle_node", "middle_node",
    reference='''
def middle_node(head):
    slow = fast = head
    while fast is not None and fast.next is not None:
        slow = slow.next
        fast = fast.next.next
    return slow
''',
    course_tests=[(([1, 2, 3, 4, 5],),), (([1, 2, 3, 4, 5, 6],),), (([1],),)],
    adversarial=lambda rng: (
        [(([1, 2],),), (([1, 2, 3],),)]
        + [((list(range(rng.randint(1, 30))),),) for _ in range(200)]
    ),
    run=lambda f, args: list_vals(f(build_list(args[0]))),
)

# ----------------------------------------------------------- reverse a list
problem(
    "reverse_list", "reverse_list",
    reference='''
def reverse_list(head):
    prev = None
    cur = head
    while cur is not None:
        nxt = cur.next
        cur.next = prev
        prev = cur
        cur = nxt
    return prev
''',
    course_tests=[(([1, 2, 3, 4, 5],),), (([1, 2],),)],
    adversarial=lambda rng: (
        [(([],),), (([7],),)]
        + [(([rng.randint(-9, 9) for _ in range(rng.randint(0, 25))],),) for _ in range(200)]
    ),
    run=lambda f, args: list_vals(f(build_list(args[0]))),
)

# ----------------------------------------------------------- validate a BST
problem(
    "is_valid_bst", "is_valid_bst",
    reference='''
def is_valid_bst(root):
    def check(node, low, high):
        if node is None:
            return True
        if node.val <= low or node.val >= high:
            return False
        return check(node.left, low, node.val) and check(node.right, node.val, high)
    return check(root, float("-inf"), float("inf"))
''',
    course_tests=[(([2, 1, 3],),), (([5, 1, 4, None, None, 3, 6],),)],
    adversarial=lambda rng: (
        [(([],),), (([1],),), (([1, 1],),), (([5, 4, 6, None, None, 3, 7],),), (([2, 2, 2],),)]
        + [((random_bst_level(rng, rng.randint(1, 15), valid=rng.random() < 0.5),),) for _ in range(300)]
    ),
    run=lambda f, args: f(build_tree(args[0])),
)

# ------------------------------------------------------- level-order traversal
problem(
    "level_order", "level_order",
    reference='''
def level_order(root):
    if root is None:
        return []
    out, level = [], [root]
    while level:
        out.append([n.val for n in level])
        nxt = []
        for n in level:
            if n.left is not None:
                nxt.append(n.left)
            if n.right is not None:
                nxt.append(n.right)
        level = nxt
    return out
''',
    course_tests=[(([3, 9, 20, None, None, 15, 7],),), (([1],),)],
    adversarial=lambda rng: (
        [(([],),), (([1, 2],),), (([1, None, 2],),), (([1, 2, 3, 4, None, None, 5],),)]
        + [((random_bst_level(rng, rng.randint(0, 15)),),) for _ in range(200)]
    ),
    run=lambda f, args: f(build_tree(args[0])),
)
