"""
Unit tests for openvoice.modules
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.openvoice.modules as modules
import torch


def test_module_importable():
    assert modules is not None


def test_LayerNorm_forward():
    ln = modules.LayerNorm(4)
    x = torch.randn(2, 4, 5)
    out = ln(x)
    assert out.shape == x.shape


def test_ConvReluNorm_forward():
    crn = modules.ConvReluNorm(4, 4, 4, 3, 2, 0.1)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    out = crn(x, x_mask)
    assert out.shape == x.shape


def test_DDSConv_forward():
    dds = modules.DDSConv(4, 3, 2, 0.1)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    out = dds(x, x_mask)
    assert out.shape == x.shape


def test_WN_forward_and_remove_weight_norm():
    wn = modules.WN(4, 3, 1, 2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    out = wn(x, x_mask)
    assert out.shape == x.shape
    wn.remove_weight_norm()


def test_ResBlock1_forward_and_remove_weight_norm():
    rb = modules.ResBlock1(4, 3, (1, 2, 3))
    x = torch.randn(2, 4, 5)
    out = rb(x)
    assert out.shape == x.shape
    rb.remove_weight_norm()


def test_ResBlock2_forward_and_remove_weight_norm():
    rb = modules.ResBlock2(4, 3, (1, 2))
    x = torch.randn(2, 4, 5)
    out = rb(x)
    assert out.shape == x.shape
    rb.remove_weight_norm()


def test_Log_forward_and_reverse():
    log = modules.Log()
    x = torch.abs(torch.randn(2, 1, 5)) + 1e-2
    x_mask = torch.ones(2, 1, 5)
    y, logdet = log(x, x_mask)
    assert y.shape == x.shape
    x_recon = log(y, x_mask, reverse=True)
    assert x_recon.shape == x.shape


def test_Flip_forward_and_reverse():
    flip = modules.Flip()
    x = torch.randn(2, 4, 5)
    y, logdet = flip(x)
    assert y.shape == x.shape
    x_recon = flip(y, reverse=True)
    assert x_recon.shape == x.shape


def test_ElementwiseAffine_forward_and_reverse():
    ea = modules.ElementwiseAffine(4)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    y, logdet = ea(x, x_mask)
    assert y.shape == x.shape
    x_recon = ea(y, x_mask, reverse=True)
    assert x_recon.shape == x.shape


def test_ResidualCouplingLayer_forward_and_reverse():
    rcl = modules.ResidualCouplingLayer(4, 4, 3, 1, 2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    y, logdet = rcl(x, x_mask)
    assert y.shape == x.shape
    x_recon = rcl(y, x_mask, reverse=True)
    assert x_recon.shape == x.shape


def test_ConvFlow_forward_and_reverse():
    cf = modules.ConvFlow(4, 4, 3, 2)
    x = torch.randn(2, 4, 5)
    x_mask = torch.ones(2, 1, 5)
    y, logdet = cf(x, x_mask)
    assert y.shape == x.shape
    x_recon = cf(y, x_mask, reverse=True)
    assert x_recon.shape == x.shape
