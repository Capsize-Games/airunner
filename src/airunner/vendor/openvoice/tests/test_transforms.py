"""
Unit tests for openvoice.transforms
Covers importability and basic function presence.
"""

import pytest
import airunner.vendor.openvoice.transforms as transforms
import torch
import numpy as np


def test_module_importable():
    assert transforms is not None


def test_piecewise_rational_quadratic_transform_basic():
    # Use input in [0, 1] to match default domain and correct shape
    x = torch.linspace(0.1, 0.9, 10)  # shape (10,)
    widths = torch.ones(10, 5)  # shape (10, 5)
    heights = torch.ones(10, 5)
    derivatives = torch.ones(10, 6)  # shape (10, 6): must be num_bins+1
    out, logabsdet = transforms.piecewise_rational_quadratic_transform(
        x, widths, heights, derivatives
    )
    assert out.shape == x.shape
    assert logabsdet.shape == x.shape


def test_piecewise_rational_quadratic_transform_with_tails():
    # Use 1D input and matching shape for tail mode
    x = torch.linspace(-0.5, 0.5, 5)
    widths = torch.ones(5, 3)
    heights = torch.ones(5, 3)
    derivatives = torch.ones(5, 3)
    out, logabsdet = transforms.piecewise_rational_quadratic_transform(
        x, widths, heights, derivatives, tails="linear", tail_bound=1.0
    )
    assert out.shape == x.shape
    assert logabsdet.shape == x.shape


def test_searchsorted():
    bins = torch.tensor([0.0, 0.5, 1.0])
    x = torch.tensor([0.1, 0.6, 0.9])
    idx = transforms.searchsorted(bins, x)
    assert torch.all(idx == torch.tensor([0, 1, 1]))


def test_unconstrained_rational_quadratic_spline_linear():
    # Use 1D input and matching shape for tail mode
    x = torch.linspace(-1, 1, 10)  # shape (10,)
    widths = torch.ones(10, 4)  # shape (10, 4)
    heights = torch.ones(10, 4)
    derivatives = torch.ones(10, 4)
    out, logabsdet = transforms.unconstrained_rational_quadratic_spline(
        x, widths, heights, derivatives, tails="linear", tail_bound=1.0
    )
    assert out.shape == x.shape
    assert logabsdet.shape == x.shape


def test_unconstrained_rational_quadratic_spline_invalid_tails():
    x = torch.zeros(2, 2)
    widths = torch.ones(2, 2)
    heights = torch.ones(2, 2)
    derivatives = torch.ones(2, 2)
    with pytest.raises(RuntimeError):
        transforms.unconstrained_rational_quadratic_spline(
            x, widths, heights, derivatives, tails="unsupported"
        )


def test_rational_quadratic_spline_domain_error():
    x = torch.tensor([-2.0, 2.0])
    widths = torch.ones(2, 2)
    heights = torch.ones(2, 2)
    derivatives = torch.ones(2, 2)
    with pytest.raises(ValueError):
        transforms.rational_quadratic_spline(x, widths, heights, derivatives)


def test_rational_quadratic_spline_min_bin_width_height():
    x = torch.tensor([0.1, 0.2])
    widths = torch.ones(2, 2)
    heights = torch.ones(2, 2)
    derivatives = torch.ones(2, 2)
    # Should not raise
    out, logabsdet = transforms.rational_quadratic_spline(
        x, widths, heights, derivatives
    )
    assert out.shape == x.shape
    assert logabsdet.shape == x.shape
    # Too large min_bin_width
    with pytest.raises(ValueError):
        transforms.rational_quadratic_spline(
            x, widths, heights, derivatives, min_bin_width=0.6
        )
    with pytest.raises(ValueError):
        transforms.rational_quadratic_spline(
            x, widths, heights, derivatives, min_bin_height=0.6
        )
