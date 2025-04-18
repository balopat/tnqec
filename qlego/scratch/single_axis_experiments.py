from galois import GF2

from legos import Legos
from qlego.tensor_network import TensorNetwork, StabilizerCodeTensorEnumerator

from sympy.abc import w, z

if __name__ == "__main__":

    rsc_x = GF2(
        [
            [1, 0, 0, 1, 0, 0, 0, 0, 0],
            [0, 1, 1, 0, 1, 1, 0, 0, 0],
            [0, 0, 0, 1, 1, 0, 1, 1, 0],
            [0, 0, 0, 0, 0, 1, 0, 0, 1],
        ]
    )

    tn = TensorNetwork.make_rsc(3, lambda i: Legos.enconding_tensor_512)
    stab_poly = tn.stabilizer_enumerator_polynomial()
    print(stab_poly)

    unnormalized_poly = (
        (
            stab_poly.homogenize(9).to_sympy([z, w]).subs({w: w - z, z: w + z}) / 256
        ).as_poly()
    ).simplify()

    coeffs = unnormalized_poly.coeffs()
    z_degrees = [m[0] for m in unnormalized_poly.monoms()]

    print({d: c for d, c in zip(z_degrees, coeffs)})

    fiveq = GF2(
        [
            [1, 0, 0, 1, 0, 0, 1, 1, 0, 0],
            [0, 1, 0, 0, 1, 0, 0, 1, 1, 0],
            [1, 0, 1, 0, 0, 0, 0, 0, 1, 1],
            [0, 1, 0, 1, 0, 1, 0, 0, 0, 1],
        ]
    )

    sc = StabilizerCodeTensorEnumerator(fiveq)
    print(sc.scalar_stabilizer_enumerator())
    print((sc.normalizer_enumerator()))
