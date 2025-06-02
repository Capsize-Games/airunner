"""
Unit tests for melo.transforms
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.melo.transforms as transforms
import torch
import numpy as np


def test_module_importable():
    assert transforms is not None


def test_piecewise_rational_quadratic_transform_basic():
    x = torch.linspace(0.1, 0.9, 10)
    widths = torch.ones(10, 5)
    heights = torch.ones(10, 5)
    derivatives = torch.ones(10, 6)
    out, logabsdet = transforms.piecewise_rational_quadratic_transform(
        x, widths, heights, derivatives
    )
    assert out.shape == x.shape
    assert logabsdet.shape == x.shape


def test_piecewise_rational_quadratic_transform_with_tails():
    x = torch.linspace(-2, 2, 10)
    widths = torch.ones(10, 5)
    heights = torch.ones(10, 5)
    derivatives = torch.ones(10, 6)
    out, logabsdet = transforms.piecewise_rational_quadratic_transform(
        x, widths, heights, derivatives, tails="linear", tail_bound=1.0
    )
    assert out.shape == x.shape
    assert logabsdet.shape == x.shape


def test_searchsorted():
    bins = torch.tensor([0.0, 0.5, 1.0])
    x = torch.tensor([0.1, 0.6, 0.9])
    idx = transforms.searchsorted(bins, x)
    assert torch.equal(idx, torch.tensor([0, 1, 1]))


def test_unconstrained_rational_quadratic_spline_linear():
    x = torch.linspace(-1, 1, 10)
    widths = torch.ones(10, 5)
    heights = torch.ones(10, 5)
    derivatives = torch.ones(10, 6)
    out, logabsdet = transforms.unconstrained_rational_quadratic_spline(
        x, widths, heights, derivatives, tails="linear", tail_bound=1.0
    )
    assert out.shape == x.shape
    assert logabsdet.shape == x.shape


def test_unconstrained_rational_quadratic_spline_invalid_tails():
    x = torch.linspace(-1, 1, 10)
    widths = torch.ones(10, 5)
    heights = torch.ones(10, 5)
    derivatives = torch.ones(10, 6)
    with pytest.raises(RuntimeError):
        transforms.unconstrained_rational_quadratic_spline(
            x, widths, heights, derivatives, tails="unsupported", tail_bound=1.0
        )


def test_rational_quadratic_spline_domain_error():
    x = torch.tensor([-2.0, 2.0])
    widths = torch.ones(2, 5)
    heights = torch.ones(2, 5)
    derivatives = torch.ones(2, 6)
    with pytest.raises(ValueError):
        transforms.rational_quadratic_spline(
            x, widths, heights, derivatives, left=0.0, right=1.0
        )


def test_rational_quadratic_spline_min_bin_width_height():
    x = torch.linspace(0.0, 1.0, 10)
    widths = torch.ones(10, 5)
    heights = torch.ones(10, 5)
    derivatives = torch.ones(10, 6)
    # Should raise if min_bin_width * num_bins > 1.0
    with pytest.raises(ValueError):
        transforms.rational_quadratic_spline(
            x, widths, heights, derivatives, min_bin_width=0.5
        )
    with pytest.raises(ValueError):
        transforms.rational_quadratic_spline(
            x, widths, heights, derivatives, min_bin_height=0.5
        )
