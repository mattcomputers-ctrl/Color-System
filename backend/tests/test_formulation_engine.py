"""Tests for the formulation engine."""

import numpy as np
import pytest

from app.services.color_science import reflectance_to_ks, spectral_to_lab, NUM_WAVELENGTHS
from app.services.formulation_engine import (
    FormulationEngine, ColorantData, FormulationResult
)


def _make_colorant(base_id, code, name, reflectance, substrate_ks):
    """Create a ColorantData from reflectance, subtracting substrate."""
    ks = reflectance_to_ks(np.array(reflectance))
    net_ks = np.maximum(ks - substrate_ks, 0.0)
    return ColorantData(
        base_id=base_id, code=code, name=name,
        ks_spectrum=net_ks, concentration_pct=100.0
    )


@pytest.fixture
def substrate_ks():
    """K/S of a white substrate (R≈0.9)."""
    return reflectance_to_ks(np.full(NUM_WAVELENGTHS, 0.9))


@pytest.fixture
def sample_colorants(substrate_ks):
    """Create a set of synthetic colorants for testing."""
    wl = np.arange(360, 781, 10, dtype=float)

    # Yellow — high reflectance above 500nm
    yellow_R = np.where(wl < 500, 0.05, 0.80)
    # Blue — high reflectance 420-520nm
    blue_R = np.where((wl > 420) & (wl < 520), 0.40, 0.03)
    # White
    white_R = np.full(NUM_WAVELENGTHS, 0.90)

    return [
        _make_colorant(1, 'Y', 'Yellow', yellow_R, substrate_ks),
        _make_colorant(2, 'B', 'Blue', blue_R, substrate_ks),
        _make_colorant(3, 'W', 'White', white_R, substrate_ks),
    ]


class TestFormulationEngine:
    def test_formulate_returns_result(self, substrate_ks, sample_colorants):
        """Engine should return a FormulationResult."""
        target_lab = (80.0, -5.0, 70.0)  # Yellowish
        engine = FormulationEngine()
        result = engine.formulate(
            target_lab=target_lab,
            colorants=sample_colorants,
            substrate_ks=substrate_ks,
        )
        assert isinstance(result, FormulationResult)
        assert result.success

    def test_components_sum_to_100(self, substrate_ks, sample_colorants):
        """Formula components should sum to ~100%."""
        target_lab = (60.0, 10.0, 30.0)
        engine = FormulationEngine()
        result = engine.formulate(
            target_lab=target_lab,
            colorants=sample_colorants,
            substrate_ks=substrate_ks,
        )
        assert result.success
        total = sum(c.percentage for c in result.components)
        assert total == pytest.approx(100.0, abs=0.1)

    def test_predicted_lab_reasonable(self, substrate_ks, sample_colorants):
        """Predicted LAB should be in valid range."""
        target_lab = (50.0, 0.0, 0.0)
        engine = FormulationEngine()
        result = engine.formulate(
            target_lab=target_lab,
            colorants=sample_colorants,
            substrate_ks=substrate_ks,
        )
        assert result.success
        L, a, b = result.predicted_lab
        assert 0 <= L <= 100
        assert -128 <= a <= 128
        assert -128 <= b <= 128

    def test_delta_e_positive(self, substrate_ks, sample_colorants):
        """Delta E should be non-negative."""
        target_lab = (50.0, 20.0, -10.0)
        engine = FormulationEngine()
        result = engine.formulate(
            target_lab=target_lab,
            colorants=sample_colorants,
            substrate_ks=substrate_ks,
        )
        assert result.success
        assert result.delta_e_76 >= 0
        assert result.delta_e_2000 >= 0

    def test_no_colorants_returns_failure(self, substrate_ks):
        """No colorants should return failure."""
        engine = FormulationEngine()
        result = engine.formulate(
            target_lab=(50.0, 0.0, 0.0),
            colorants=[],
            substrate_ks=substrate_ks,
        )
        assert not result.success

    def test_spectral_target(self, substrate_ks, sample_colorants):
        """Formulation with spectral target data."""
        # Create a target reflectance (mid-grey)
        target_R = np.full(NUM_WAVELENGTHS, 0.5)
        engine = FormulationEngine()
        result = engine.formulate(
            target_reflectance=target_R,
            colorants=sample_colorants,
            substrate_ks=substrate_ks,
        )
        assert result.success
        assert len(result.predicted_reflectance) == NUM_WAVELENGTHS

    def test_formulate_multi(self, substrate_ks, sample_colorants):
        """Multi-result formulation should return multiple alternatives."""
        target_lab = (60.0, 0.0, 40.0)
        engine = FormulationEngine()
        results = engine.formulate_multi(
            target_lab=target_lab,
            colorants=sample_colorants,
            substrate_ks=substrate_ks,
            num_results=3,
        )
        assert len(results) >= 1
        # Results should be sorted by delta_e_2000
        for i in range(len(results) - 1):
            assert results[i].delta_e_2000 <= results[i + 1].delta_e_2000
