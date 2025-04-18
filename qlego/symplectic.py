from typing import List
from galois import GF2
import numpy as np


def weight(op: GF2, skip_indices: List[int] = []):
    """Calculate the weight of a symplectic operator."""
    n = len(op) // 2
    x_inds = np.array([i for i in range(n) if i not in skip_indices])
    z_inds = x_inds + n
    if len(x_inds) == 0 and len(z_inds) == 0:
        return 0
    return np.count_nonzero(op[x_inds] | op[z_inds])


def symp_to_str(vec, swapxz=False):
    p = ["I", "X", "Z", "Y"]
    if swapxz:
        p = ["I", "Z", "X", "Y"]
    n = len(vec) // 2

    return "".join([p[2 * int(vec[i + n]) + int(vec[i])] for i in range(n)])


def omega(n):
    return GF2(
        np.block(
            [
                [GF2.Zeros((n, n)), GF2.Identity(n)],
                [GF2.Identity(n), GF2.Zeros((n, n))],
            ]
        )
    )


def sslice(op, indices):
    n = len(op) // 2

    if isinstance(indices, list | np.ndarray):
        if len(indices) == 0:
            return GF2([])
        indices = np.array(indices)
        return GF2(np.concatenate([op[indices], op[indices + n]]))
    elif isinstance(indices, slice):
        x = slice(
            0 if indices.start is None else indices.start,
            n if indices.stop is None else indices.stop,
        )

        z = slice(x.start + n, x.stop + n)
        return GF2(np.concatenate([op[x], op[z]]))


def _suboperator_matches_on_support(support, op, subop):
    if len(support) == 0:
        return len(subop) == 0
    m = len(support)
    n = len(op) // 2
    support = np.array(support)
    return (
        # Xs equal
        np.array_equal(op[support], subop[:m])
        and
        # Zs equal
        np.array_equal(op[support + n], subop[m:])
    )


def _equal_on_support(support, op1, op2):
    n1 = len(op1) // 2
    n2 = len(op2) // 2
    support = np.array(support)
    return (
        # Xs equal
        np.array_equal(op1[support], op2[support])
        and
        # Zs equal
        np.array_equal(op1[support + n1], op2[support + n2])
    )


def replace_with_op_on_indices(indices, op, target):
    """replaces target's operations with op

    op should have self.m number of qubits, target should have self.n qubits.
    """
    m = len(indices)
    n = len(op) // 2

    res = target.copy()
    res[indices] = op[:m]
    res[np.array(indices) + n] = op[m:]
    return res


def sconcat(*ops):
    ns = [len(op) // 2 for op in ops]
    return np.hstack(
        [  # X part
            np.concatenate([op[:n] for n, op in zip(ns, ops)]),
            # Z part
            np.concatenate([op[n:] for n, op in zip(ns, ops)]),
        ]
    )
