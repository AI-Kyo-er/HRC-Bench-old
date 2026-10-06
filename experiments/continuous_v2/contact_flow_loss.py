"""OpenPI flow matching with real temporal support and separate physical action loss.

The original 32-dimensional sampler is preserved. Its 24 padded dimensions have
a separately reported auxiliary loss so they remain denoised during inference.
Only the first eight dimensions describe physical actions in this dataset.
"""
import jax
import jax.numpy as jnp

from openpi.models import model as model_lib
from openpi.models.pi0 import make_attn_mask


def reduce_flow_errors(errors, valid):
    weights = jnp.asarray(valid, dtype=errors.dtype)
    denominator = jnp.maximum(jnp.sum(weights), 1)
    active = jnp.sum(jnp.mean(errors[..., :8], axis=-1) * weights) / denominator
    padding = jnp.sum(jnp.mean(errors[..., 8:], axis=-1) * weights) / denominator
    return active, padding


def contact_flow_loss(model, rng, observation, actions, valid, *, train=False):
    """Same noise/time distribution as Pi0.compute_loss; masks absent suffix keys."""
    if not model.pi05:
        raise ValueError("This loss requires the pi05 action-only suffix")
    preprocess_rng, noise_rng, time_rng = jax.random.split(rng, 3)
    observation = model_lib.preprocess_observation(preprocess_rng, observation, train=train)
    noise = jax.random.normal(noise_rng, actions.shape)
    time = jax.random.beta(time_rng, 1.5, 1, actions.shape[:-2]) * 0.999 + 0.001
    expanded = time[..., None, None]
    noisy = jnp.where(valid[..., None], expanded * noise + (1 - expanded) * actions, 0)
    target = noise - actions
    prefix, prefix_mask, prefix_ar = model.embed_prefix(observation)
    suffix, suffix_mask, suffix_ar, conditioning = model.embed_suffix(observation, noisy, time)
    suffix_mask = suffix_mask & valid
    inputs = jnp.concatenate([prefix_mask, suffix_mask], axis=1)
    ar = jnp.concatenate([prefix_ar, suffix_ar], axis=0)
    (_, output), _ = model.PaliGemma.llm(
        [prefix, suffix], mask=make_attn_mask(inputs, ar),
        positions=jnp.cumsum(inputs, axis=1) - 1, adarms_cond=[None, conditioning])
    prediction = model.action_out_proj(output[:, -model.action_horizon:])
    # Mask before reduction as well: arbitrary/nonfinite filler is never a target.
    errors = jnp.where(valid[..., None], jnp.square(prediction - target), 0)
    return reduce_flow_errors(errors, valid)
