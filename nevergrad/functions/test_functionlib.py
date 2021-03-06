# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from typing import Any, Dict
import numpy as np
from ..common import testing
from . import functionlib


DESCRIPTION_KEYS = {"function_class", "name", "block_dimension", "useful_dimensions", "useless_variables", "translation_factor",
                    "num_blocks", "rotation", "noise_level", "dimension", "discrete", "aggregator", "hashing",
                    "instrumentation", "noise_dissymmetry"}


def test_testcase_function_errors() -> None:
    config: Dict[str, Any] = {"name": "blublu", "block_dimension": 3, "useless_variables": 6, "num_blocks": 2}
    np.testing.assert_raises(ValueError, functionlib.ArtificialFunction, **config)  # blublu does not exist
    config.update(name="sphere")
    functionlib.ArtificialFunction(**config)  # should wor
    config.update(num_blocks=0)
    np.testing.assert_raises(ValueError, functionlib.ArtificialFunction, **config)  # num blocks should be > 0
    config.update(num_blocks=2.)
    np.testing.assert_raises(TypeError, functionlib.ArtificialFunction, **config)  # num blocks should be > 0
    config.update(num_blocks=2, rotation=1)
    np.testing.assert_raises(TypeError, functionlib.ArtificialFunction, **config)  # num blocks should be > 0


def test_artitificial_function_repr() -> None:
    config: Dict[str, Any] = {"name": "sphere", "block_dimension": 3, "useless_variables": 6, "num_blocks": 2}
    func = functionlib.ArtificialFunction(**config)
    output = repr(func)
    assert "sphere" in output, f"Unexpected representation: {output}"


@testing.parametrized(
    sphere=({"name": "sphere", "block_dimension": 3, "useless_variables": 6, "num_blocks": 2}, 9.630),
    cigar=({"name": "cigar", "block_dimension": 3, "useless_variables": 6, "num_blocks": 2}, 3527289.665),
    cigar_rot=({"rotation": True, "name": "cigar", "block_dimension": 3, "useless_variables": 6, "num_blocks": 2}, 5239413.576),
    no_transform=({"name": "leadingones5", "block_dimension": 50, "useless_variables": 10}, 9.0),
    hashed=({"name": "sphere", "block_dimension": 3, "useless_variables": 6, "num_blocks": 2, "hashing": True}, 12.44),
    noisy_sphere=({"name": "sphere", "block_dimension": 3, "useless_variables": 6, "num_blocks": 2, "noise_level": .2}, 9.576),
    noisy_very_sphere=({"name": "sphere", "block_dimension": 3, "useless_variables": 6,
                        "num_blocks": 2, "noise_dissymmetry": True, "noise_level": .2}, 7.615),
)
def test_testcase_function_value(config: Dict[str, Any], expected: float) -> None:
    # make sure no change is made to the computation
    func = functionlib.ArtificialFunction(**config)
    np.random.seed(2)
    x = np.random.normal(0, 1, func.dimension)
    x *= -1 if config.get("noise_dissymmetry", False) else 1  # change sign to activate noise dissymetry
    if config.get("hashing", False):
        x = str(x)
    np.random.seed(12)  # function randomness comes at first call
    value = func(x)
    np.testing.assert_almost_equal(value, expected, decimal=3)


@testing.parametrized(
    random=(np.random.normal(0, 1, 12), False),
    hashed=("abcdefghijkl", True),
)
def test_test_function(x: Any, hashing: bool) -> None:
    config: Dict[str, Any] = {"name": "sphere", "block_dimension": 3, "useless_variables": 6, "num_blocks": 2, "hashing": hashing}
    outputs = []
    for _ in range(2):
        np.random.seed(12)
        func = functionlib.ArtificialFunction(**config)
        outputs.append(func(x))
    np.testing.assert_equal(outputs[0], outputs[1])
    # make sure it is properly random otherwise
    outputs.append(functionlib.ArtificialFunction(**config)(x))
    assert outputs[1] != outputs[2]


def test_oracle() -> None:
    func = functionlib.ArtificialFunction("sphere", 5, noise_level=.1)
    x = np.array([1, 2, 1, 0, .5])
    y1 = func(x)  # returns a float
    y2 = func(x)  # returns a different float since the function is noisy
    np.testing.assert_raises(AssertionError, np.testing.assert_array_almost_equal, y1, y2)
    y3 = func.noisefree_function(x)   # returns a float
    y4 = func.noisefree_function(x)   # returns the same float (no noise for oracles + sphere function is deterministic)
    np.testing.assert_array_almost_equal(y3, y4)  # should be different


def test_function_transform() -> None:
    func = functionlib.ArtificialFunction("sphere", 2, num_blocks=1, noise_level=.1)
    output = func._transform(np.array([0., 0]))
    np.testing.assert_equal(output.shape, (1, 2))
    np.testing.assert_equal(len([x for x in output]), 1)


def test_artificial_function_summary() -> None:
    func = functionlib.ArtificialFunction("sphere", 5)
    testing.assert_set_equal(func.descriptors.keys(), DESCRIPTION_KEYS)
    np.testing.assert_equal(func.descriptors["function_class"], "ArtificialFunction")


def test_duplicate() -> None:
    func = functionlib.ArtificialFunction("sphere", 5, noise_level=.2, num_blocks=4)
    func2 = func.duplicate()
    assert func == func2
    assert func._parameters["noise_level"] == func2._parameters["noise_level"]
    assert func is not func2


def test_artifificial_function_with_jump() -> None:
    func1 = functionlib.ArtificialFunction("sphere", 5)
    func2 = functionlib.ArtificialFunction("jump5", 5)
    np.testing.assert_equal(func1.transform_var.only_index_transform, False)
    np.testing.assert_equal(func2.transform_var.only_index_transform, True)


def test_get_postponing_delay() -> None:
    x = np.array([2., 2])
    func = functionlib.ArtificialFunction("sphere", 2)
    np.testing.assert_equal(func.get_postponing_delay((x,), {}, 3), 1.)
    np.random.seed(12)
    func = functionlib.ArtificialFunction("DelayedSphere", 2)
    np.testing.assert_almost_equal(func.get_postponing_delay((x,), {}, 3), 0.0010534)
    # check minimum
    np.random.seed(None)
    func = functionlib.ArtificialFunction("DelayedSphere", 2)
    func([0, 0])  # trigger init
    x = func.transform_var._transforms[0].translation
    np.testing.assert_equal(func(x), 0)
    np.testing.assert_equal(func.get_postponing_delay((x,), {}, 0), 0)


@testing.parametrized(
    no_noise=(2, False, False, False),
    noise=(2, True, False, True),
    noise_dissymmetry_pos=(2, True, True, False),  # no noise on right side
    noise_dissymmetry_neg=(-2, True, True, True),
    no_noise_with_dissymmetry_neg=(-2, False, True, False),
)
def test_noisy_call(x: int, noise: bool, noise_dissymmetry: bool, expect_noisy: bool) -> None:
    fx = functionlib._noisy_call(x=np.array([x]),
                                 transf=np.tanh,
                                 func=lambda y: np.arctanh(y)[0],  # type: ignore
                                 noise_level=float(noise),
                                 noise_dissymmetry=noise_dissymmetry)
    assert not np.isnan(fx)  # noise addition should not get out of function domain
    if expect_noisy:
        np.testing.assert_raises(AssertionError, np.testing.assert_almost_equal, fx, x, decimal=8)
    else:
        np.testing.assert_almost_equal(fx, x, decimal=8)
