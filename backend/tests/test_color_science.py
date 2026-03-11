"""Tests for color science calculations.

These tests verify the core mathematical operations used in formulation.
Reference values are from published CIE data and known test cases.
"""

import numpy as np
import pytest

from app.services.color_science import (
    spectral_to_xyz, xyz_to_lab, spectral_to_lab,
    delta_e_76, delta_e_2000,
    reflectance_to_ks, ks_to_reflectance,
    NUM_WAVELENGTHS,
)


class TestSpectralToXYZ:
    def test_perfect_white(self):
        """Perfect diffuser (R=1.0 everywhere) should give Y=100."""
        white = np.ones(NUM_WAVELENGTHS)
        X, Y, Z = spectral_to_xyz(white)
        assert abs(Y - 100.0) < 0.5  # Y should be ~100

    def test_perfect_black(self):
        """Near-zero reflectance should give near-zero tristimulus values."""
        black = np.full(NUM_WAVELENGTHS, 0.01)
        X, Y, Z = spectral_to_xyz(black)
        assert Y < 2.0

    def test_output_shape(self):
        """Should return three floats."""
        r = np.random.uniform(0.0, 1.0, NUM_WAVELENGTHS)
        result = spectral_to_xyz(r)
        assert len(result) == 3
        assert all(isinstance(v, (float, np.floating)) for v in result)


class TestXYZToLAB:
    def test_white_point(self):
        """D50 white point should give L*=100, a*=0, b*=0."""
        from app.services.color_science import D50_XN, D50_YN, D50_ZN
        L, a, b = xyz_to_lab(D50_XN, D50_YN, D50_ZN)
        assert abs(L - 100.0) < 0.01
        assert abs(a) < 0.01
        assert abs(b) < 0.01

    def test_black(self):
        """Black (Y=0) should give L*=0."""
        L, a, b = xyz_to_lab(0.0, 0.0, 0.0)
        assert abs(L - 0.0) < 1.0

    def test_mid_grey(self):
        """50% reflectance grey should give L* around 76."""
        from app.services.color_science import D50_XN, D50_YN, D50_ZN
        L, a, b = xyz_to_lab(D50_XN * 0.5, D50_YN * 0.5, D50_ZN * 0.5)
        # L* of 50% reflectance is ~76.07 (CIE formula)
        assert 70 < L < 80


class TestDeltaE:
    def test_identical_colors(self):
        """Delta E between identical colors should be 0."""
        lab = (50.0, 20.0, -10.0)
        assert delta_e_76(lab, lab) == pytest.approx(0.0, abs=1e-10)
        assert delta_e_2000(lab, lab) == pytest.approx(0.0, abs=1e-10)

    def test_delta_e_76_simple(self):
        """Basic CIE76 computation."""
        lab1 = (50.0, 0.0, 0.0)
        lab2 = (53.0, 4.0, 0.0)
        expected = np.sqrt(3**2 + 4**2)  # 5.0
        assert delta_e_76(lab1, lab2) == pytest.approx(expected, abs=1e-6)

    def test_delta_e_2000_known_pair(self):
        """CIEDE2000 test with values from Sharma et al. (2005) supplementary data.

        Pair 1: L1=50.0, a1=2.6772, b1=-79.7751
                L2=50.0, a2=0.0,    b2=-82.7485
                Expected ΔE₀₀ = 2.0425
        """
        lab1 = (50.0, 2.6772, -79.7751)
        lab2 = (50.0, 0.0, -82.7485)
        de = delta_e_2000(lab1, lab2)
        assert de == pytest.approx(2.0425, abs=0.005)

    def test_delta_e_2000_symmetry(self):
        """ΔE should be symmetric."""
        lab1 = (50.0, 25.0, -10.0)
        lab2 = (60.0, 10.0, 5.0)
        assert delta_e_2000(lab1, lab2) == pytest.approx(delta_e_2000(lab2, lab1), abs=1e-10)


class TestKubelkaMunk:
    def test_roundtrip(self):
        """R -> K/S -> R should be identity."""
        R = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
        ks = reflectance_to_ks(R)
        R_back = ks_to_reflectance(ks)
        np.testing.assert_allclose(R_back, R, atol=0.01)

    def test_high_reflectance_low_ks(self):
        """High reflectance should give low K/S."""
        R = np.array([0.9])
        ks = reflectance_to_ks(R)
        assert ks[0] < 0.01

    def test_low_reflectance_high_ks(self):
        """Low reflectance should give high K/S."""
        R = np.array([0.05])
        ks = reflectance_to_ks(R)
        assert ks[0] > 5.0

    def test_ks_monotonic(self):
        """K/S should decrease as reflectance increases."""
        R = np.linspace(0.05, 0.95, 20)
        ks = reflectance_to_ks(R)
        assert all(ks[i] > ks[i + 1] for i in range(len(ks) - 1))
