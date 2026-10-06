"""Small CPU checks for the physical supervision contract, without model weights."""
from types import SimpleNamespace

import numpy as np
import pytest

jax = pytest.importorskip("jax")
jnp = pytest.importorskip("jax.numpy")
pytest.importorskip("openpi")
from experiments.continuous_v2 import contact_flow_loss as flow


def test_physical_dimensions_are_not_diluted_by_padding_and_invalid_steps():
    errors = jnp.ones((1, 3, 32)).at[..., 8:].set(9).at[:, 2, :].set(10000)
    valid = jnp.array([[True, True, False]])
    active, padding = flow.reduce_flow_errors(errors, valid)
    assert float(active) == 1
    assert float(padding) == 9
    gradient = jax.grad(lambda value: flow.reduce_flow_errors(value, valid)[0])(errors)
    np.testing.assert_array_equal(gradient[:, 2], 0)
    np.testing.assert_array_equal(gradient[..., 8:], 0)


def test_absent_future_actions_cannot_condition_valid_predictions(monkeypatch):
    monkeypatch.setattr(flow.model_lib, "preprocess_observation", lambda rng, obs, train: obs)
    masks = []

    def llm(tokens, *, mask, positions, adarms_cond):
        masks.append(np.asarray(mask))
        values = jnp.concatenate(tokens, axis=1)
        output = jnp.einsum("bij,bjd->bid", mask.astype(values.dtype), values)
        return (output[:, :1], output[:, 1:]), None

    model = SimpleNamespace(
        pi05=True, action_horizon=3,
        embed_prefix=lambda obs: (jnp.zeros((1, 1, 32)), jnp.ones((1, 1), bool), jnp.array([False])),
        embed_suffix=lambda obs, actions, time: (actions, jnp.ones((1, 3), bool),
                                                jnp.array([True, False, False]), None),
        action_out_proj=lambda output: output,
        PaliGemma=SimpleNamespace(llm=llm))
    valid = jnp.array([[True, True, False]])
    actions = jnp.zeros((1, 3, 32))
    first = flow.contact_flow_loss(model, jax.random.key(0), None, actions, valid)
    second = flow.contact_flow_loss(model, jax.random.key(0), None, actions.at[:, 2, :].set(1e6), valid)
    np.testing.assert_allclose(first, second)
    assert not masks[0][:, :3, 3].any()
