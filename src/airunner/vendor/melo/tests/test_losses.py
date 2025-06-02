"""
Unit tests for melo.losses
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.melo.losses as losses
import torch
import numpy as np


def test_module_importable():
    assert losses is not None


# --- feature_loss ---
def test_feature_loss_basic():
    fmap_r = [[torch.ones(2, 3), torch.zeros(2, 3)], [torch.full((2, 3), 2.0)]]
    fmap_g = [[torch.zeros(2, 3), torch.ones(2, 3)], [torch.full((2, 3), 1.0)]]
    loss = losses.feature_loss(fmap_r, fmap_g)
    # Each mean: mean(abs(1-0))=1, mean(abs(0-1))=1, mean(abs(2-1))=1, so sum=3, then *2=6
    assert torch.isclose(loss, torch.tensor(6.0))


def test_feature_loss_empty():
    assert losses.feature_loss([], []) == 0


def test_feature_loss_correct_value():
    # The previous test expected 36.0, but the function sums means, not elementwise diffs.
    # For fmap_r = [[ones, zeros], [full(2)]], fmap_g = [[zeros, ones], [full(1)]]
    # Means: mean(abs(1-0))=1, mean(abs(0-1))=1, mean(abs(2-1))=1, so sum=1+1+1=3, then *2=6
    fmap_r = [[torch.ones(2, 3), torch.zeros(2, 3)], [torch.full((2, 3), 2.0)]]
    fmap_g = [[torch.zeros(2, 3), torch.ones(2, 3)], [torch.full((2, 3), 1.0)]]
    loss = losses.feature_loss(fmap_r, fmap_g)
    assert torch.isclose(loss, torch.tensor(6.0))


# --- discriminator_loss ---
def test_discriminator_loss_basic():
    dr = [torch.ones(2, 3)]
    dg = [torch.zeros(2, 3)]
    loss, r_losses, g_losses = losses.discriminator_loss(dr, dg)
    # r_loss = mean((1-1)^2)=0, g_loss=mean(0^2)=0, so loss=0
    assert loss == 0
    assert r_losses == [0.0]
    assert g_losses == [0.0]


def test_discriminator_loss_nontrivial():
    dr = [torch.full((2, 3), 0.5)]
    dg = [torch.full((2, 3), 0.2)]
    loss, r_losses, g_losses = losses.discriminator_loss(dr, dg)
    # r_loss = mean((1-0.5)^2)=0.25, g_loss=mean(0.2^2)=0.04, total=0.25+0.04=0.29
    assert np.isclose(loss.item(), 0.29, atol=1e-2)
    assert np.isclose(r_losses[0], 0.25, atol=1e-2)
    assert np.isclose(g_losses[0], 0.04, atol=1e-2)


def test_discriminator_loss_shape_mismatch():
    # The function does not raise, it just zips and processes up to shortest
    dr = [torch.ones(2, 3)]
    dg = [torch.ones(2, 2), torch.ones(2, 2)]
    # Should not raise
    losses.discriminator_loss(dr, dg)


# --- generator_loss ---
def test_generator_loss_basic():
    dg = [torch.ones(2, 3)]
    loss, gen_losses = losses.generator_loss(dg)
    # mean((1-1)^2)=0
    assert loss == 0
    assert torch.all(torch.stack(gen_losses) == 0)


def test_generator_loss_nontrivial():
    dg = [torch.full((2, 3), 0.5)]
    loss, gen_losses = losses.generator_loss(dg)
    # mean((1-0.5)^2)=0.25, only one tensor, so loss=0.25
    assert torch.isclose(loss, torch.tensor(0.25))
    assert torch.isclose(gen_losses[0], torch.tensor(0.25))


def test_generator_loss_empty():
    loss, gen_losses = losses.generator_loss([])
    assert loss == 0
    assert gen_losses == []


# --- kl_loss ---
def test_kl_loss_basic():
    z_p = torch.zeros(2, 3, 4)
    logs_q = torch.zeros(2, 3, 4)
    m_p = torch.zeros(2, 3, 4)
    logs_p = torch.zeros(2, 3, 4)
    z_mask = torch.ones(2, 3, 4)
    l = losses.kl_loss(z_p, logs_q, m_p, logs_p, z_mask)
    # All zeros, so kl = -0.5, sum = -0.5*24 = -12, l = -12/24 = -0.5
    assert torch.isclose(l, torch.tensor(-0.5))


def test_kl_loss_masked():
    z_p = torch.zeros(2, 3, 4)
    logs_q = torch.zeros(2, 3, 4)
    m_p = torch.zeros(2, 3, 4)
    logs_p = torch.zeros(2, 3, 4)
    z_mask = torch.zeros(2, 3, 4)
    l = losses.kl_loss(z_p, logs_q, m_p, logs_p, z_mask)
    # No elements, should be nan (0/0)
    assert torch.isnan(l)


def test_kl_loss_nontrivial():
    z_p = torch.ones(2, 3, 4)
    logs_q = torch.zeros(2, 3, 4)
    m_p = torch.zeros(2, 3, 4)
    logs_p = torch.zeros(2, 3, 4)
    z_mask = torch.ones(2, 3, 4)
    l = losses.kl_loss(z_p, logs_q, m_p, logs_p, z_mask)
    # kl = -0.5 + 0.5*(1^2)*1 = 0, so sum=0, l=0
    assert torch.isclose(l, torch.tensor(0.0))
