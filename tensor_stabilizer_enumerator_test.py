from copy import deepcopy
from galois import GF2
import numpy as np
import pytest
import scipy
import sympy

from parity_check import conjoin
from scalar_stabilizer_enumerator import ScalarStabilizerCodeEnumerator
from symplectic import weight
from tensor_stabilizer_enumerator import (
    PAULI_X,
    PAULI_Z,
    SimplePoly,
    TensorNetwork,
    TensorStabilizerCodeEnumerator,
    sslice,
)

from sympy.abc import w, z
from sympy import Poly


def test_422_logical_legs_enumerator():
    enc_tens_422 = GF2(
        [
            # fmt: off
    #        l1,2            l1,2 
    [1,1,1,1, 0,0,  0,0,0,0,  0,0],
    [0,0,0,0, 0,0,  1,1,1,1,  0,0], 
    # X1
    [1,1,0,0, 1,0,  0,0,0,0,  0,0],
    # X2
    [1,0,0,1, 0,1,  0,0,0,0,  0,0],       
    # Z2
    [0,0,0,0, 0,0,  1,1,0,0,  0,1],
    # Z1
    [0,0,0,0, 0,0,  1,0,0,1,  1,0],
            # fmt: on
        ]
    )

    tensorwe_on_log_legs = TensorStabilizerCodeEnumerator(enc_tens_422)

    assert {4: 3, 0: 1} == tensorwe_on_log_legs.stabilizer_enumerator(
        [4, 5], e=GF2.Zeros(4), eprime=GF2.Zeros(4)
    )


def test_422_physical_legs_off_diagonlas():
    enc_tens_422 = GF2(
        [
            # fmt: off
    #        l1,2            l1,2 
    [1,1,1,1, 0,0,  0,0,0,0,  0,0],
    [0,0,0,0, 0,0,  1,1,1,1,  0,0], 
    # X1
    [1,1,0,0, 1,0,  0,0,0,0,  0,0],
    # X2
    [1,0,0,1, 0,1,  0,0,0,0,  0,0],       
    # Z2
    [0,0,0,0, 0,0,  1,1,0,0,  0,1],
    # Z1
    [0,0,0,0, 0,0,  1,0,0,1,  1,0],
            # fmt: on
        ]
    )
    vec_enum_phys_legs = TensorStabilizerCodeEnumerator(enc_tens_422)
    assert {0: 2} == vec_enum_phys_legs.stabilizer_enumerator(
        traced_legs=[0, 1, 2, 3], e=GF2([1, 1, 1, 1, 0, 0, 0, 0]), eprime=GF2.Zeros(8)
    )


def test_steane_logical_legs():
    steane_tensor = GF2(
        [
            # fmt: off
            [1, 0, 0, 1, 1, 0, 0, 1,   0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0,   1, 1, 0, 0, 1, 1, 0, 0],
            [1, 1, 1, 1, 0, 0, 0, 0,   0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0,   1, 1, 1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 1, 1, 1,   0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0,   1, 0, 0, 1, 1, 0, 0, 1],
            [1, 1, 0, 0, 1, 1, 0, 0,   0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 1, 1, 1, 1],
            # fmt: on
        ]
    )
    tensorwe_on_log_legs = TensorStabilizerCodeEnumerator(steane_tensor)

    h = GF2(
        [
            [1, 0, 1, 0, 1, 0, 1],
            [0, 1, 1, 0, 0, 1, 1],
            [0, 0, 0, 1, 1, 1, 1],
        ]
    )

    steane_parity = GF2(scipy.linalg.block_diag(h, h))

    we = ScalarStabilizerCodeEnumerator(steane_parity).stabilizer_enumerator

    assert we == tensorwe_on_log_legs.stabilizer_enumerator(
        traced_legs=[0], e=GF2.Zeros(2), eprime=GF2.Zeros(2)
    )


def test_trace_two_422_codes_into_steane():
    enc_tens_422 = GF2(
        [
            # fmt: off
    #        l1,2            l1,2 
    [1,1,1,1, 0,0,  0,0,0,0,  0,0],
    [0,0,0,0, 0,0,  1,1,1,1,  0,0], 
    # X1
    [1,1,0,0, 1,0,  0,0,0,0,  0,0],
    # X2
    [1,0,0,1, 0,1,  0,0,0,0,  0,0],       
    # Z2
    [0,0,0,0, 0,0,  1,1,0,0,  0,1],
    # Z1
    [0,0,0,0, 0,0,  1,0,0,1,  1,0],
            # fmt: on
        ]
    )

    t1 = TensorStabilizerCodeEnumerator(enc_tens_422)
    t2 = deepcopy(t1)

    # we join the two tensors via the tracked legs (4,4)
    t3 = t2.conjoin(t1, [4, 5], [4, 5])

    steane = GF2(
        [
            # fmt: off
            [1, 0, 0, 1, 1, 0, 0, 1,   0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0,   1, 1, 0, 0, 1, 1, 0, 0],            
            [0, 0, 0, 0, 1, 1, 1, 1,   0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0,   0, 0, 0, 0, 1, 1, 1, 1],
            [0, 0, 0, 0, 0, 0, 0, 0,   1, 1, 1, 1, 0, 0, 0, 0],            
            [0, 0, 0, 0, 0, 0, 0, 0,   1, 0, 0, 1, 1, 0, 0, 1],
            [1, 1, 1, 1, 0, 0, 0, 0,   0, 0, 0, 0, 0, 0, 0, 0],
            [1, 1, 0, 0, 1, 1, 0, 0,   0, 0, 0, 0, 0, 0, 0, 0],
            # fmt: on
        ]
    )

    assert np.array_equal(t3.h, steane), f"Not equal:\n{t3.h}"

    assert {6: 42, 4: 21, 0: 1} == t3.stabilizer_enumerator(
        traced_legs=[0], e=GF2.Zeros(2), eprime=GF2.Zeros(2)
    )


def test_trace_two_422_codes_into_steane_v2():
    enc_tens_422 = GF2(
        [
            # fmt: off
    #        l1,2            l1,2 
    [1,1,1,1, 0,0,  0,0,0,0,  0,0],
    [0,0,0,0, 0,0,  1,1,1,1,  0,0], 
    # X1
    [1,1,0,0, 1,0,  0,0,0,0,  0,0],
    # X2
    [1,0,0,1, 0,1,  0,0,0,0,  0,0],       
    # Z2
    [0,0,0,0, 0,0,  1,1,0,0,  0,1],
    # Z1
    [0,0,0,0, 0,0,  1,0,0,1,  1,0],
            # fmt: on
        ]
    )

    t1 = TensorStabilizerCodeEnumerator(enc_tens_422)
    t2 = deepcopy(t1)

    t3 = TensorNetwork(nodes=[t1, t2])
    t3.self_trace(0, 1, [4, 5], [4, 5])

    assert {6: 42, 4: 21, 0: 1} == t3.stabilizer_enumerator(
        0, legs=[(0, 0)], e=GF2.Zeros(2), eprime=GF2.Zeros(2)
    )


def test_stopper_tensors():
    enc_tens_422 = GF2(
        [
            # fmt: off
    #        l1,2            l1,2 
    [1,1,1,1, 0,0,  0,0,0,0,  0,0],
    [0,0,0,0, 0,0,  1,1,1,1,  0,0], 
    # X1
    [1,1,0,0, 1,0,  0,0,0,0,  0,0],
    # X2
    [1,0,0,1, 0,1,  0,0,0,0,  0,0],       
    # Z2
    [0,0,0,0, 0,0,  1,1,0,0,  0,1],
    # Z1
    [0,0,0,0, 0,0,  1,0,0,1,  1,0],
            # fmt: on
        ]
    )

    node = TensorStabilizerCodeEnumerator(enc_tens_422)
    node = node.trace_with_stopper(stopper=PAULI_Z, traced_leg=3)

    assert np.array_equal(
        node.h,
        GF2(
            [
                # 0  1  2  4  5  0  1  2  4  5
                [0, 0, 0, 0, 0, 1, 1, 1, 0, 0],
                # X1
                [1, 1, 0, 1, 0, 0, 0, 0, 0, 0],
                # X2
                [0, 1, 1, 0, 1, 0, 0, 0, 0, 0],
                # Z2
                [0, 0, 0, 0, 0, 1, 1, 0, 0, 1],
                # Z1
                [0, 0, 0, 0, 0, 0, 1, 1, 1, 0],
            ]
        ),
    ), f"Not equal: \n{repr(node.h)}"

    assert node.legs == [0, 1, 2, 4, 5]

    with pytest.raises(ValueError):
        node.trace_with_stopper(stopper=GF2([0, 1]), traced_leg=3)

    node = node.trace_with_stopper(stopper=PAULI_X, traced_leg=0)

    assert np.array_equal(
        node.h,
        GF2(
            [
                # 1  2  4  5  1  2  4  5
                # X1
                [1, 0, 1, 0, 0, 0, 0, 0],
                # X2
                [1, 1, 0, 1, 0, 0, 0, 0],
                # Z2
                [0, 0, 0, 0, 0, 1, 0, 1],
                # Z1
                [0, 0, 0, 0, 1, 1, 1, 0],
            ]
        ),
    ), f"Not equal: \n{repr(node.h)}"


def test_open_legged_enumerator():
    enc_tens_422 = GF2(
        [
            # fmt: off
    #        l1,2            l1,2 
    [1,1,1,1, 0,0,  0,0,0,0,  0,0],
    [0,0,0,0, 0,0,  1,1,1,1,  0,0], 
    # X1
    [1,1,0,0, 1,0,  0,0,0,0,  0,0],
    # X2
    [1,0,0,1, 0,1,  0,0,0,0,  0,0],       
    # Z2
    [0,0,0,0, 0,0,  1,1,0,0,  0,1],
    # Z1
    [0,0,0,0, 0,0,  1,0,0,1,  1,0],
            # fmt: on
        ]
    )

    t1 = TensorStabilizerCodeEnumerator(enc_tens_422, idx=5)

    t2 = t1.stabilizer_enumerator_polynomial([4, 5], open_legs=[0, 1])

    assert t2 == {
        ((0, 0, 0, 0), (0, 0, 0, 0)): SimplePoly({0: 1}),
        ((0, 0, 1, 1), (0, 0, 1, 1)): SimplePoly({2: 1}),
        ((1, 1, 0, 0), (1, 1, 0, 0)): SimplePoly({2: 1}),
        ((1, 1, 1, 1), (1, 1, 1, 1)): SimplePoly({2: 1}),
    }, f"not equal:\n{t2}"


def test_partially_traced_enumerator():
    pytest.skip()
    enc_tens_422 = GF2(
        [
            # fmt: off
    #        l1,2            l1,2 
    [1,1,1,1, 0,0,  0,0,0,0,  0,0],
    [0,0,0,0, 0,0,  1,1,1,1,  0,0], 
    # X1
    [1,1,0,0, 1,0,  0,0,0,0,  0,0],
    # X2
    [1,0,0,1, 0,1,  0,0,0,0,  0,0],       
    # Z2
    [0,0,0,0, 0,0,  1,1,0,0,  0,1],
    # Z1
    [0,0,0,0, 0,0,  1,0,0,1,  1,0],
            # fmt: on
        ]
    )

    t1 = TensorStabilizerCodeEnumerator(enc_tens_422, idx=5)
    t2 = TensorStabilizerCodeEnumerator(enc_tens_422, idx=3)

    # pytest.fail()
    pte = t1.trace_with(
        t2,
        join_legs1=[2],
        join_legs2=[1],
        traced_legs1=[4, 5],
        traced_legs2=[4, 5],
        e1=GF2.Zeros(4),
        eprime1=GF2.Zeros(4),
        e2=GF2.Zeros(4),
        eprime2=GF2.Zeros(4),
        open_legs1=[1],
        open_legs2=[2, 3],
    )

    assert pte.tracable_legs == [(5, 1), (3, 2), (3, 3)]
    assert pte.tensor == {
        ((0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0)): Poly(w**12, w, z, domain="ZZ"),
        ((0, 0, 0, 1, 1, 1), (0, 0, 0, 1, 1, 1)): Poly(w**9 * z**3, w, z, domain="ZZ"),
        ((1, 1, 1, 0, 0, 0), (1, 1, 1, 0, 0, 0)): Poly(w**9 * z**3, w, z, domain="ZZ"),
        ((1, 1, 1, 1, 1, 1), (1, 1, 1, 1, 1, 1)): Poly(w**9 * z**3, w, z, domain="ZZ"),
    }

    t3 = TensorStabilizerCodeEnumerator(enc_tens_422, idx=4)

    pte = pte.trace_with(
        t3,
        join_legs1=[(5, 1)],
        join_legs2=[0],
        traced_legs=[4, 5],
        e=GF2.Zeros(4),
        eprime=GF2.Zeros(4),
        open_legs1=[(3, 2), (3, 3)],
        open_legs2=[2, 3],
    )
    assert pte.nodes == {5, 3, 4}
    assert pte.tracable_legs == [(3, 2), (3, 3), (4, 2), (4, 3)]
    assert pte.tensor == {
        ((0, 0, 0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0, 0)): Poly(
            w**18, w, z, domain="ZZ"
        ),
        ((0, 0, 0, 0, 1, 1, 1, 1), (0, 0, 0, 0, 1, 1, 1, 1)): Poly(
            w**14 * z**4, w, z, domain="ZZ"
        ),
        ((1, 1, 1, 1, 0, 0, 0, 0), (1, 1, 1, 1, 0, 0, 0, 0)): Poly(
            w**14 * z**4, w, z, domain="ZZ"
        ),
        ((1, 1, 1, 1, 1, 1, 1, 1), (1, 1, 1, 1, 1, 1, 1, 1)): Poly(
            w**14 * z**4, w, z, domain="ZZ"
        ),
    }


def test_step_by_step_to_d2_surface_code():
    # pytest.skip()

    enc_tens_512 = GF2(
        [
            # fmt: off
    #        l1,2            l1,2 
    [1,1,1,1, 0,  0,0,0,0,  0,],
    [0,0,0,0, 0,  1,1,1,1,  0,], 
    # X1
    [1,1,0,0, 1,  0,0,0,0,  0,],        
    # Z1
    [0,0,0,0, 0,  1,0,0,1,  1,],
            # fmt: on
        ]
    )

    t0 = (
        TensorStabilizerCodeEnumerator(enc_tens_512, idx=0)
        .trace_with_stopper(PAULI_Z, 3)
        .trace_with_stopper(PAULI_X, 0)
    )

    print(t0.legs)
    print(t0.h)

    t1 = (
        TensorStabilizerCodeEnumerator(enc_tens_512, idx=1)
        .trace_with_stopper(PAULI_Z, 0)
        .trace_with_stopper(PAULI_X, 3)
    )

    print(t1.legs)
    print(t1.h)

    h_pte = t0.conjoin(t1, [2], [1])

    print(h_pte.h)
    for i in range(2**3):
        picked_generators = GF2(list(np.binary_repr(i, width=3)), dtype=int)
        stabilizer = picked_generators @ h_pte.h
        print(
            stabilizer,
            weight(stabilizer),
            sslice(stabilizer, [1, 2]),
            weight(stabilizer, [1, 2]),
        )

    brute_force_wep = h_pte.stabilizer_enumerator()
    print(brute_force_wep)

    # pytest.fail()
    pte = t0.trace_with(
        t1,
        join_legs1=[2],
        join_legs2=[1],
        traced_legs1=[],
        traced_legs2=[],
        e1=GF2([]),
        eprime1=GF2([]),
        e2=GF2([]),
        eprime2=GF2([]),
        open_legs1=[1],
        open_legs2=[2],
    )

    assert pte.nodes == {0, 1}
    assert pte.tracable_legs == [(0, 1), (1, 2)]

    total_wep = SimplePoly()
    for k, sub_wep in pte.tensor.items():

        print(k, "->", sub_wep / 16, sub_wep / 16 * SimplePoly({weight(GF2(k[0])): 1}))
        total_wep.add_inplace(sub_wep / 16 * SimplePoly({weight(GF2(k[0])): 1}))

    assert brute_force_wep == total_wep._dict

    pytest.fail()

    t2 = (
        TensorStabilizerCodeEnumerator(enc_tens_512, idx=2)
        .trace_with_stopper(PAULI_X, 1)
        .trace_with_stopper(PAULI_Z, 2)
    )

    t3 = (
        TensorStabilizerCodeEnumerator(enc_tens_512, idx=3)
        .trace_with_stopper(PAULI_X, 2)
        .trace_with_stopper(PAULI_Z, 1)
    )


def test_double_trace_422():
    enc_tens_422 = GF2(
        [
            # fmt: off
    #        l1,2            l1,2 
    [1,1,1,1, 0,0,  0,0,0,0,  0,0],
    [0,0,0,0, 0,0,  1,1,1,1,  0,0], 
    # X1
    [1,1,0,0, 1,0,  0,0,0,0,  0,0],
    # X2
    [1,0,0,1, 0,1,  0,0,0,0,  0,0],       
    # Z2
    [0,0,0,0, 0,0,  1,1,0,0,  0,1],
    # Z1
    [0,0,0,0, 0,0,  1,0,0,1,  1,0],
            # fmt: on
        ]
    )
    nodes = [
        TensorStabilizerCodeEnumerator(enc_tens_422),
        TensorStabilizerCodeEnumerator(enc_tens_422),
    ]

    tn = TensorNetwork(nodes)
    tn.self_trace(0, 1, [1, 2], [2, 1])

    wep = tn.stabilizer_enumerator(0, [(0, 4), (0, 5), (1, 4), (1, 5)])
    print(wep)

    assert wep == {4: 3, 0: 1}


def test_d3_rotated_surface_code():
    pytest.skip()
    rsc = GF2(
        [
            [1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1],
        ]
    )

    scalar = ScalarStabilizerCodeEnumerator(rsc)
    print(scalar.stabilizer_enumerator)
    enc_tens_512 = GF2(
        [
            # fmt: off
    #        l1            l1 
    [1,1,1,1, 0,  0,0,0,0,  0],
    [0,0,0,0, 0,  1,1,1,1,  0], 
    # X1
    [1,1,0,0, 1,  0,0,0,0,  0],    
    # Z1
    [0,0,0,0, 0,  1,0,0,1,  1],
            # fmt: on
        ]
    )

    nodes = [TensorStabilizerCodeEnumerator(enc_tens_512, idx=i) for i in range(9)]

    # top Z boundary
    nodes[0] = nodes[0].trace_with_stopper(PAULI_Z, 3)
    nodes[1] = nodes[1].trace_with_stopper(PAULI_Z, 0)
    nodes[2] = nodes[2].trace_with_stopper(PAULI_Z, 3)

    # bottom Z boundary
    nodes[6] = nodes[6].trace_with_stopper(PAULI_Z, 1)
    nodes[7] = nodes[7].trace_with_stopper(PAULI_Z, 2)
    nodes[8] = nodes[8].trace_with_stopper(PAULI_Z, 1)

    # left X boundary
    nodes[0] = nodes[0].trace_with_stopper(PAULI_X, 0)
    nodes[3] = nodes[3].trace_with_stopper(PAULI_X, 1)
    nodes[6] = nodes[6].trace_with_stopper(PAULI_X, 0)

    # right X boundary
    nodes[2] = nodes[2].trace_with_stopper(PAULI_X, 2)
    nodes[5] = nodes[5].trace_with_stopper(PAULI_X, 3)
    nodes[8] = nodes[8].trace_with_stopper(PAULI_X, 2)

    tn = TensorNetwork(nodes)

    tn.self_trace(0, 3, [1], [0])
    tn.self_trace(3, 6, [2], [3])

    tn.self_trace(0, 1, [2], [1])
    tn.self_trace(3, 4, [3], [0])
    tn.self_trace(6, 7, [2], [1])

    tn.self_trace(1, 2, [3], [0])
    tn.self_trace(4, 5, [2], [1])
    tn.self_trace(7, 8, [3], [0])

    tn.self_trace(1, 4, [2], [3])
    tn.self_trace(2, 5, [1], [0])

    tn.self_trace(4, 7, [1], [0])
    tn.self_trace(5, 8, [2], [3])

    assert tn.open_legs == [
        [1, 2],
        [1, 3, 2],
        [0, 1],
        [0, 2, 3],
        [0, 2, 3, 1],
        [1, 0, 2],
        [3, 2],
        [1, 3, 0],
        [0, 3],
    ]

    we = tn.stabilizer_enumerator(
        0,
        legs=[(idx, 4) for idx in range(9)],
    )

    assert we == {8: 129, 6: 100, 4: 22, 2: 4, 0: 1}


# # legs - left, bottom, right, top
# even and odd nodes are rotated by 90 degrees
# phys = [[0,1], [1,2],[2,3],[3,0]]
# left, bottom, right, top = range(4)
# idx = lambda r, c: r*3 + c

# r = 0
# for c in range(3):
#     n = idx[r,c]
#     nodes[n].trace_with_stopper(PAULI_Z, phys[top][n%2])
# r = 2
# for c in range(3):
#     n = idx[r,c]
#     nodes[n].trace_with_stopper(PAULI_Z, phys[bottom][n%2])
# c = 0
# for r in range(3):
#     n = idx[r,c]
#     nodes[n].trace_with_stopper(PAULI_X, phys[left][n%2])
# c = 3
# for r in range(3):
#     n = idx[r,c]
#     nodes[n].trace_with_stopper(PAULI_X, phys[right][n%2])