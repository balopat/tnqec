from collections import defaultdict
from typing import List, Dict, Set, Tuple, Union
from galois import GF2
import numpy as np
import sympy

from linalg import gauss
from parity_check import conjoin, self_trace, sprint
from scalar_stabilizer_enumerator import ScalarStabilizerCodeEnumerator
from symplectic import omega, weight

from sympy.abc import w, z

from tensor_legs import TensorLegs

PAULI_X = GF2([1, 0])
PAULI_Z = GF2([0, 1])
PAULI_Y = GF2([1, 1])


class SimplePoly:
    def __init__(self, d=None):
        self._dict = defaultdict(int) if d is None else d

    def add_inplace(self, other):

        for k, v in other._dict.items():
            self._dict[k] += v

    def __add__(self, other):
        if isinstance(other, SimplePoly):
            res = SimplePoly(self._dict.copy())
            for k, v in other._dict.items():
                res._dict[k] += v
            return res
        elif isinstance(other, int):
            res = SimplePoly(self._dict.copy())
            for k in self._dict.keys():
                res._dict[k] += other
            return res
        else:
            raise ValueError(f"Unsupported type to add to SimplePoly: {type(other)}")

    def __str__(self):
        return str(dict(self._dict))

    def __repr__(self):
        return f"SimplePoly({repr(self._dict)})"

    def __truediv__(self, n):
        if isinstance(n, int | float):
            # TODO: is this really a good idea to always keep coeffs integer?
            return SimplePoly({k: v // n for k, v in self._dict.items()})

    def __lmul__(self, n):
        return self.__mul__(n)

    def __rmul__(self, n):
        return self.__mul__(n)

    def __eq__(self, value):
        if isinstance(value, int | float):
            return self._dict[0] == value
        return self._dict == value._dict

    def __hash__(self):
        return hash(self._dict)

    def __mul__(self, n):
        if isinstance(n, int | float):
            return SimplePoly({k: n * v for k, v in self._dict.items()})
        elif isinstance(n, SimplePoly):
            res = SimplePoly()
            for d1, coeff1 in self._dict.items():
                for d2, coeff2 in n._dict.items():
                    res._dict[d1 + d2] += coeff1 * coeff2
            return res


def _paulis(n):
    """Yields the length 2*n GF2 symplectic Pauli operators on n qubits."""
    for i in range(2 ** (2 * n)):
        yield GF2(list(np.binary_repr(i, width=2 * n)))


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


def sconcat(op1, op2):
    n1 = len(op1) // 2
    n2 = len(op2) // 2

    return np.concatenate(
        [  # X part
            np.concatenate([op1[:n1], op2[:n2]]),
            # Z part
            np.concatenate([op1[n1:], op2[n2:]]),
        ]
    )


class TensorNetwork:
    def __init__(self, nodes: List["TensorStabilizerCodeEnumerator"]):
        self.nodes = nodes
        self.traces = []
        self.open_legs = [[] for _ in self.nodes]

    def self_trace(self, node_idx1, node_idx2, join_legs1, join_legs2):
        self.traces.append((node_idx1, node_idx2, join_legs1, join_legs2))
        self.open_legs[node_idx1] += join_legs1
        self.open_legs[node_idx2] += join_legs2

    def stabilizer_enumerator_polynomial(
        self, legs: List[Tuple[int, int]], e: GF2 = None, eprime: GF2 = None
    ) -> SimplePoly:
        m = len(legs)
        node_legs = {node: [] for node in range(len(self.nodes))}
        for idx, (node, leg) in enumerate(legs):
            node_legs[node].append((leg, idx))

        # default to the identity
        if e is None:
            e = GF2.Zeros(2 * m)
        if eprime is None:
            eprime = GF2.Zeros(2 * m)
        assert len(e) == m * 2
        assert len(eprime) == m * 2

        pte: PartiallyTracedEnumerator = None

        for node_idx1, node_idx2, join_legs1, join_legs2 in self.traces:
            print(f"==== trace { node_idx1, node_idx2, join_legs1, join_legs2} ==== ")

            traced_legs_with_op_indices1 = node_legs[node_idx1]
            traced_legs1 = [l for l, idx in traced_legs_with_op_indices1]
            e1_indices = [idx for l, idx in traced_legs_with_op_indices1]
            e1 = sslice(e, e1_indices)
            eprime1 = sslice(eprime, e1_indices)

            assert len(e1) == len(eprime1)

            traced_legs_with_op_indices2 = node_legs[node_idx2]
            traced_legs2 = [l for l, idx in traced_legs_with_op_indices2]
            e2_indices = [idx for l, idx in traced_legs_with_op_indices2]
            e2 = sslice(e, e2_indices)
            eprime2 = sslice(eprime, e2_indices)

            assert len(e2) == len(eprime2)

            t2 = self.nodes[node_idx2]

            if pte is None:
                t1: TensorStabilizerCodeEnumerator = self.nodes[node_idx1]
                open_legs1 = [
                    leg for leg in self.open_legs[node_idx1] if leg not in join_legs1
                ]
                open_legs2 = [
                    leg for leg in self.open_legs[node_idx2] if leg not in join_legs2
                ]

                pte = t1.trace_with(
                    t2,
                    join_legs1=join_legs1,
                    join_legs2=join_legs2,
                    traced_legs1=traced_legs1,
                    traced_legs2=traced_legs2,
                    e1=e1,
                    eprime1=eprime1,
                    e2=e2,
                    eprime2=eprime2,
                    open_legs1=open_legs1,
                    open_legs2=open_legs2,
                )
                self.open_legs[node_idx1] = open_legs1
                self.open_legs[node_idx2] = open_legs2
            else:
                if node_idx1 not in pte.nodes:
                    raise ValueError(
                        f"Disconnected contraction schedule. {node_idx1} is not in the contracted nodes: {pte.nodes}."
                    )
                open_legs1 = [
                    (node_idx, leg)
                    for node_idx, leg in pte.tracable_legs
                    if (node_idx == node_idx1 and leg not in join_legs1)
                    or (node_idx == node_idx2 and leg not in join_legs2)
                    or (node_idx not in [node_idx1, node_idx2])
                ]
                print(f"open_legs: {open_legs1}")
                open_legs2 = [
                    leg for leg in self.open_legs[node_idx2] if leg not in join_legs2
                ]
                pte = pte.trace_with(
                    t2,
                    join_legs1=[(node_idx1, leg) for leg in join_legs1],
                    join_legs2=join_legs2,
                    traced_legs=traced_legs2,
                    e=e2,
                    eprime=eprime2,
                    open_legs1=open_legs1,
                    open_legs2=open_legs2,
                )

                self.open_legs[node_idx1] = [
                    leg for leg in self.open_legs[node_idx1] if leg not in join_legs1
                ]
                self.open_legs[node_idx2] = open_legs2

            print(f"PTE nodes: {pte.nodes}")
            print(f"PTE tracable legs: {pte.tracable_legs}")
            print(f"PTE tensor: {dict(pte.tensor)}")

        return pte.tensor[((), ())]

    def stabilizer_enumerator(
        self, k, legs: List[Tuple[int, List[int]]], e: GF2 = None, eprime: GF2 = None
    ):
        wep = self.stabilizer_enumerator_polynomial(legs, e, eprime)
        if wep == 0:
            return {}
        unnormalized_poly = wep / 4**k
        return unnormalized_poly._dict


class PartiallyTracedEnumerator:
    def __init__(
        self, nodes: Set[int], tracable_legs: List[Tuple[int, int]], tensor: np.ndarray
    ):
        self.nodes = nodes
        self.tracable_legs = tracable_legs
        self.tensor = tensor

        tensor_key_length = len(list(self.tensor.keys())[0][0])
        assert tensor_key_length == 2 * len(
            tracable_legs
        ), f"tensor keys of length {tensor_key_length} != {2 * len(tracable_legs)} (2 * len tracable legs)"

    def stabilizer_enumerator(self, legs: List[Tuple[int, int]], e, eprime):
        filtered_axes = [self.tracable_legs.index(leg) for leg in legs]
        indices = [slice(None) for _ in range(self.tracable_legs)]
        for idx, axis in enumerate(filtered_axes[: len(e)]):
            indices[axis] = int(e[idx])

        for idx, axis in enumerate(filtered_axes[len(e) :]):
            indices[axis] = int(eprime[idx])

        return self.tensor[indices]

    def trace_with(
        self,
        other: "TensorStabilizerCodeEnumerator",
        join_legs1,
        join_legs2,
        traced_legs,
        e: GF2,
        eprime: GF2,
        open_legs1,
        open_legs2,
    ) -> "PartiallyTracedEnumerator":

        assert len(join_legs1) == len(join_legs2)
        join_length = len(join_legs1)

        t2 = other.stabilizer_enumerator_polynomial(
            traced_legs, e, eprime, join_legs2 + open_legs2
        )

        open_length = len(join_legs1 + open_legs1) + len(join_legs2 + open_legs2)

        wep = defaultdict(lambda: SimplePoly())

        print(f"traceable legs: {self.tracable_legs} <- {open_legs1}")
        join_indices1 = [self.tracable_legs.index(leg) for leg in join_legs1]

        print(f"join indices1: {join_indices1}")
        join_indices2 = list(range(len(join_legs2)))

        kept_indices1 = [
            i for i, leg in enumerate(self.tracable_legs) if leg in open_legs1
        ]
        print(f"kept indices 1: {kept_indices1}")
        kept_indices2 = list(range(len(join_legs2), len(join_legs2 + open_legs2)))

        print(f"kept indices 2: {kept_indices2}")

        for k1 in self.tensor.keys():
            for k2 in t2.keys():
                if not np.array_equal(
                    sslice(GF2(k1[0]), join_indices1),
                    sslice(GF2(k2[0]), join_indices2),
                ) or not np.array_equal(
                    sslice(GF2(k1[1]), join_indices1),
                    sslice(GF2(k2[1]), join_indices2),
                ):
                    continue

                wep1 = self.tensor[k1]
                wep2 = t2[k2]
                k1 = GF2(k1[0]), GF2(k1[1])
                k2 = GF2(k2[0]), GF2(k2[1])

                # we have to cut off the join legs from both keys and concatenate them

                key = (
                    # e
                    tuple(
                        sconcat(
                            sslice(k1[0], kept_indices1),
                            sslice(k2[0], kept_indices2),
                        ).tolist()
                    ),
                    # eprime
                    tuple(
                        sconcat(
                            sslice(k1[1], kept_indices1),
                            sslice(k2[1], kept_indices2),
                        ).tolist()
                    ),
                )

                assert len(key[0]) == 2 * (
                    len(open_legs1) + len(open_legs2)
                ), f"key length: {len(key[0])} != 2*({len(open_legs1)}  + {len(open_legs2)}) = {2 * (
                    len(open_legs1) + len(open_legs2)
                )}"

                wep[key] += wep1 * wep2

        tracable_legs = [(idx, leg) for idx, leg in open_legs1]
        tracable_legs += [(other.idx, leg) for leg in open_legs2]

        return PartiallyTracedEnumerator(
            self.nodes.union({other.idx}), tracable_legs=tracable_legs, tensor=wep
        )


class TensorStabilizerCodeEnumerator:
    """The tensor enumerator from Cao & Lackey"""

    def __init__(self, h, idx=0, legs=None):
        self.h = h

        self.idx = idx
        if len(self.h) == 0:
            self.n = 0
            self.k = 0
        elif len(self.h.shape) == 1:
            self.n = self.h.shape[0] // 2
            self.k = self.n - 1
        else:
            self.n = self.h.shape[1] // 2
            self.k = self.n - self.h.shape[0]

        self.legs = list(range(self.n)) if legs is None else legs
        assert (
            len(self.legs) == self.n
        ), f"Leg number {len(self.legs)} does not match parity check matrix columns (qubit count) {self.n}"
        # a dict is a wonky tensor - TODO: rephrase this to proper tensor
        self._stabilizer_enums: Dict[sympy.Tuple, SimplePoly] = {}

    def _key(self, e, eprime):

        return (
            tuple(e.astype(np.uint8).tolist()),
            tuple(eprime.astype(np.uint8).tolist()),
        )

    def is_stabilizer(self, op):
        return 0 == np.count_nonzero(op @ omega(self.n) @ self.h.T)

    def _remove_leg(self, legs, leg):
        del legs[leg]
        for k in legs.keys():
            if k > leg:
                legs[k] -= 1

    def _remove_legs(self, legs, legs_to_remove):
        for leg in legs_to_remove:
            self._remove_leg(legs, leg)

    def validate_legs(self, legs):
        return [leg for leg in legs if not leg in self.legs]

    def trace_with(
        self,
        other: "TensorStabilizerCodeEnumerator",
        join_legs1,
        join_legs2,
        traced_legs1,
        traced_legs2,
        e1: GF2,
        eprime1: GF2,
        e2: GF2,
        eprime2: GF2,
        open_legs1,
        open_legs2,
    ):

        invalid_legs = self.validate_legs(join_legs1)
        assert (
            invalid_legs == []
        ), f"invalid legs to join on for tensor {self.idx}: {invalid_legs}"
        invalid_legs = self.validate_legs(open_legs1)
        assert (
            invalid_legs == []
        ), f"invalid legs to leave open for tensor {self.idx}: {invalid_legs}"

        invalid_legs = other.validate_legs(join_legs2)
        assert (
            invalid_legs == []
        ), f"invalid legs to join on for tensor {other.idx}: {invalid_legs}"
        invalid_legs = other.validate_legs(open_legs2)
        assert (
            invalid_legs == []
        ), f"invalid legs to leave open for tensor {other.idx}: {invalid_legs}"

        assert len(join_legs1) == len(join_legs2)
        join_length = len(join_legs1)

        t1 = self.stabilizer_enumerator_polynomial(
            traced_legs1, e1, eprime1, join_legs1 + open_legs1
        )
        t2 = other.stabilizer_enumerator_polynomial(
            traced_legs2, e2, eprime2, join_legs2 + open_legs2
        )

        open_length = len(join_legs1 + open_legs1) + len(join_legs2 + open_legs2)

        wep = defaultdict(lambda: SimplePoly())

        for k1 in t1.keys():
            for k2 in t2.keys():
                if not _equal_on_support(
                    list(range(join_length)),
                    GF2(k1[0]),
                    GF2(k2[0]),
                ) or not _equal_on_support(
                    list(range(join_length)),
                    GF2(k1[1]),
                    GF2(k2[1]),
                ):
                    continue

                wep1 = t1[k1]
                wep2 = t2[k2]
                k1_gf2 = GF2(k1[0]), GF2(k1[1])
                k2_gf2 = GF2(k2[0]), GF2(k2[1])

                # we have to cut off the join legs from both keys and concatenate them

                key = (
                    # e
                    tuple(
                        sconcat(
                            sslice(k1_gf2[0], slice(join_length, None)),
                            sslice(k2_gf2[0], slice(join_length, None)),
                        ).tolist()
                    ),
                    # eprime
                    tuple(
                        sconcat(
                            sslice(k1_gf2[1], slice(join_length, None)),
                            sslice(k2_gf2[1], slice(join_length, None)),
                        ).tolist()
                    ),
                )

                wep[key].add_inplace(wep1 * wep2)

        tracable_legs = [(self.idx, leg) for leg in open_legs1]
        tracable_legs += [(other.idx, leg) for leg in open_legs2]

        return PartiallyTracedEnumerator(
            {self.idx, other.idx}, tracable_legs=tracable_legs, tensor=wep
        )

    def conjoin(self, other, legs1, legs2) -> "TensorStabilizerCodeEnumerator":
        """Creates a new brute force tensor enumerator by conjoining two of them.

        The legs of the other will become the legs of the new one. Only the index of this
        tensor preserved.
        """
        assert len(legs1) == len(legs2)
        n2 = other.n

        legs2_offset = max(self.legs) + 1

        legs = {leg: i for i, leg in enumerate(self.legs)}
        # for example 2 3 4 | 2 4 8 will become
        # as legs2_offset = 5
        # {2: 0, 3: 1, 4: 2, 7: 3, 11: 4, 13: 5}
        legs.update(
            {leg + legs2_offset: legs2_offset + i for i, leg in enumerate(other.legs)}
        )

        new_h = conjoin(
            self.h, other.h, self.legs.index(legs1[0]), other.legs.index(legs2[0])
        )
        self._remove_legs(legs, [legs1[0], legs2_offset + legs2[0]])

        for leg1, leg2 in zip(legs1[1:], legs2[1:]):
            new_h = self_trace(new_h, legs[leg1], legs[leg2 + legs2_offset])
            self._remove_legs(legs, [leg1, leg2 + legs2_offset])

        new_legs = [leg for leg in self.legs if leg not in legs1]
        new_legs += [len(new_legs) + i for i in range(n2 - len(legs2))]

        return TensorStabilizerCodeEnumerator(new_h, idx=self.idx, legs=new_legs)

    def _brute_force_stabilizer_enumerator_from_parity(
        self, traced_legs: List[int], e=None, eprime=None, open_legs=[]
    ):

        traced_cols = [self.legs.index(leg) for leg in traced_legs]
        open_cols = [self.legs.index(leg) for leg in open_legs]

        if open_cols is None:
            open_cols = []

        is_diagonal_element = np.array_equal(e, eprime)
        if not is_diagonal_element:
            # check if EE' \prod_J I^(n-m) is a stabilizer

            if not self.is_stabilizer(
                replace_with_op_on_indices(
                    traced_cols, e + eprime, GF2.Zeros(self.n * 2)
                )
            ):
                return 0

        class SimpleStabilizerCollector:
            def __init__(self, k, n):
                self.k = k
                self.n = n
                self.wep = SimplePoly()
                self.skip_indices = np.concatenate([traced_cols, open_cols])

            def collect(self, stabilizer):
                stab_weight = weight(stabilizer, skip_indices=self.skip_indices)
                self.wep.add_inplace(SimplePoly({stab_weight: 1}))

            def finalize(self):
                self.wep = 4**self.k * self.wep

        class DoubleStabilizerCollector:
            def __init__(self, k, n):
                self.k = k
                self.n = n
                self.simple = len(open_cols) == 0
                self.skip_indices = np.concatenate([traced_cols, open_cols])

                self.matching_stabilizers = []
                self.wep = defaultdict(lambda: SimplePoly())

            def collect(self, stabilizer):
                print(stabilizer)
                self.matching_stabilizers.append(stabilizer)

            def _scale_one(self, wep):
                return 4**self.k * wep

            def finalize(self):
                print("finalizing...")
                # complement indices
                tlc = [leg for leg in range(self.n) if leg not in traced_cols]
                olc = [leg for leg in range(self.n) if leg not in open_cols]

                for s1 in self.matching_stabilizers:
                    w1 = weight(s1, tlc)
                    stab_weight = weight(s1, skip_indices=self.skip_indices)
                    for s2 in self.matching_stabilizers:
                        w2 = weight(s1, tlc)
                        if w2 != w1:
                            continue
                        if not _suboperator_matches_on_support(
                            olc, s1, sslice(s2, olc)
                        ):
                            continue
                        self.wep[
                            (
                                tuple(sslice(s1, open_cols).tolist()),
                                tuple(sslice(s2, open_cols).tolist()),
                            )
                        ].add_inplace(SimplePoly({stab_weight: 1}))

                for key in self.wep.keys():
                    self.wep[key] = self._scale_one(self.wep[key])

        collector = (
            SimpleStabilizerCollector(self.k, self.n)
            if open_cols == []
            else DoubleStabilizerCollector(self.k, self.n)
        )
        # assuming a full rank parity check
        for i in range(2 ** (self.n - self.k)):
            picked_generators = GF2(
                list(np.binary_repr(i, width=(self.n - self.k))), dtype=int
            )
            stabilizer = picked_generators @ self.h

            if is_diagonal_element and not _suboperator_matches_on_support(
                traced_cols, stabilizer, e
            ):
                # we are only interested in stabilizers that have the diagonal element on indices
                continue
            elif not is_diagonal_element:
                # we want to count stabilizers that one of the off-diagonal components
                # a non-zero count would mean that there is a stabilizer for both
                matching_off_diagonals = (
                    _suboperator_matches_on_support(traced_cols, stabilizer, e)
                    and self.is_stabilizer(
                        replace_with_op_on_indices(traced_cols, eprime, stabilizer)
                    )
                ) or (
                    _suboperator_matches_on_support(traced_cols, stabilizer, eprime)
                    and self.is_stabilizer(
                        replace_with_op_on_indices(traced_cols, e, stabilizer)
                    )
                )
                if not matching_off_diagonals:
                    continue
            collector.collect(stabilizer)
        collector.finalize()
        return collector.wep

    def stabilizer_enumerator_polynomial(
        self,
        traced_legs: List[int] = [],
        e: GF2 = None,
        eprime: GF2 = None,
        open_legs=[],
    ) -> SimplePoly:
        """Stabilizer enumerator polynomial.

        If traced_legs and open_legs left empty, it gives the scalar stabilizer enumerator polynomial.
        If traced_legs is not empty, the enumerators will be traced over those legs with E and E' (represented by e, eprime).
        If open_legs is not empty, then the result is a sparse tensor, with non-zero values on the open_legs.
        """
        m = len(traced_legs)
        if e is None:
            e = GF2.Zeros(2 * m)
        if eprime is None:
            eprime = e.copy()
        assert len(e) == m * 2, f"{len(e)} != {m*2}"
        assert len(eprime) == m * 2, f"{len(eprime)} != {m*2}"

        wep = self._brute_force_stabilizer_enumerator_from_parity(
            traced_legs, e, eprime, open_legs=open_legs
        )
        return wep

    def stabilizer_enumerator(
        self,
        traced_legs: List[int] = [],
        e: GF2 = None,
        eprime: GF2 = None,
        open_legs=[],
    ):
        if open_legs is not None and len(open_legs) > 0:
            raise ValueError("only polynomials are allowed with open legs.")
        unnormalized_poly = (
            self.stabilizer_enumerator_polynomial(
                traced_legs,
                e,
                eprime,
                open_legs=open_legs,
            )
            / 4**self.k
        )

        return unnormalized_poly._dict

    def trace_with_stopper(self, stopper: GF2, traced_leg: int):
        if traced_leg not in self.legs:
            raise ValueError(f"can't trace on {traced_leg} - no such leg.")
        # other = TensorStabilizerCodeEnumerator(stopper, legs=[0])
        # return self.conjoin(other, [traced_leg], [0])
        kept_cols = list(range(2 * self.n))
        kept_cols.remove(self.legs.index(traced_leg))
        kept_cols.remove(self.legs.index(traced_leg) + self.n)
        kept_cols = np.array(kept_cols)
        h_new = gauss(
            self.h,
            col_subset=[
                self.legs.index(traced_leg),
                self.legs.index(traced_leg) + self.n,
            ],
        )

        h_new = GF2(
            [
                row[kept_cols]
                for row in h_new
                if _suboperator_matches_on_support([traced_leg], row, stopper)
                or _suboperator_matches_on_support([traced_leg], row, GF2([0, 0]))
            ]
        )
        kept_legs = self.legs.copy()
        kept_legs.remove(traced_leg)

        return TensorStabilizerCodeEnumerator(h=h_new, idx=self.idx, legs=kept_legs)