# Flaw-validity audit report

Candidates audited: **40** across 5 problems.
Course suite = the few lab-style tests per problem. Adversarial suite = edge cases plus randomised inputs checked against the reference solution (binary_search: 306, middle_node: 202, reverse_list: 202, is_valid_bst: 305, level_order: 204 inputs).

## Observed outcome

| outcome | count | share |
|---|---|---|
| course_fail | 32 | 80% |
| adversarial_only | 7 | 18% |
| no_observed_defect | 1 | 2% |
| load_error | 0 | 0% |

## By intended flaw type

| intended flaw | course_fail | adversarial_only | no_observed_defect | load_error |
|---|---|---|---|---|
| and_or_swap | 3 | 0 | 0 | 0 |
| boundary_or_comparison | 9 | 2 | 1 | 0 |
| dropped_branch | 6 | 1 | 0 | 0 |
| dropped_pointer_update | 1 | 0 | 0 | 0 |
| off_by_one_constant | 4 | 2 | 0 | 0 |
| wrong_pointer | 9 | 2 | 0 | 0 |

## By problem

| problem | course_fail | adversarial_only | no_observed_defect | load_error |
|---|---|---|---|---|
| binary_search | 8 | 2 | 1 | 0 |
| is_valid_bst | 7 | 2 | 0 | 0 |
| level_order | 7 | 3 | 0 | 0 |
| middle_node | 7 | 0 | 0 | 0 |
| reverse_list | 3 | 0 | 0 | 0 |

## Examples that pass the lab-style tests but are wrong

**binary_search-mut08** (constant changed to 2)

```python
def search(nums, target):
    lo, hi = (0, len(nums) - 1)
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 2
        else:
            hi = mid - 1
    return -1
```
Counterexample: `{"input": [[1, 3], 3], "got": "-1", "expected": "1"}`

**binary_search-mut09** (constant changed to 2)

```python
def search(nums, target):
    lo, hi = (0, len(nums) - 1)
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 2
    return -1
```
Counterexample: `{"input": [[-89, -68, -67, -52, -44, -40, -26, -18, 22, 23, 30, 44, 54, 68, 72, 77, 89, 97], 54], "got": "-1", "expected": "12"}`

**is_valid_bst-mut04** (comparison changed to Lt)

```python
def is_valid_bst(root):

    def check(node, low, high):
        if node is None:
            return True
        if node.val < low or node.val >= high:
            return False
        return check(node.left, low, node.val) and check(node.right, node.val, high)
    return check(root, float('-inf'), float('inf'))
```
Counterexample: `{"input": [[-27, null, 11, -27, 20, null, null, 15, 31]], "got": "True", "expected": "False"}`

**is_valid_bst-mut05** (comparison changed to Gt)

```python
def is_valid_bst(root):

    def check(node, low, high):
        if node is None:
            return True
        if node.val <= low or node.val > high:
            return False
        return check(node.left, low, node.val) and check(node.right, node.val, high)
    return check(root, float('-inf'), float('inf'))
```
Counterexample: `{"input": [[1, 1]], "got": "True", "expected": "False"}`

**level_order-mut00** (body of if at line 3 removed)

```python
def level_order(root):
    if root is None:
        pass
    out, level = ([], [root])
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
```
Counterexample: `{"input": [[]], "got": "EXC:AttributeError", "expected": "[]"}`

## How to read this

- `adversarial_only` is the share a lab autograder would have passed. A test-based filter applied before serving would keep these, but a filter that required the lab tests to fail would throw them away.
- `no_observed_defect` is not the same as correct. Some are equivalent mutants; others may be wrong on inputs we did not try. These need human adjudication.
- For mutants the intended flaw is known. For LLM output it is only claimed, so intent and observed defect are reported in separate columns and never merged.
