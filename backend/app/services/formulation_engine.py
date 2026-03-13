"""Ink formulation engine using Kubelka-Munk theory.

This module implements the core formulation algorithm that determines the optimal
mix of colorant bases to match a target color.

Theory:
  Kubelka-Munk single-constant theory states that K/S values are additive
  for mixtures. For a mixture of N colorants at concentrations c_i:

    (K/S)_mix = Σ c_i · (K/S)_i

  where (K/S)_i is the K/S spectrum of colorant i at unit concentration.

  The K/S spectrum of each colorant is derived from its measured reflectance
  at a known concentration against a known substrate:

    (K/S)_colorant = (K/S)_measured - (K/S)_substrate

  The predicted reflectance of the mixture is:

    R_predicted = 1 + (K/S)_mix - sqrt((K/S)_mix² + 2·(K/S)_mix)

  The optimal formula minimizes color difference (CIEDE2000) between the
  predicted and target colors.

Optimization:
  We use scipy.optimize.minimize with the SLSQP method, which supports
  the constraint that all concentrations sum to 1.0 (100%) and are non-negative.

  The optimizer minimizes CIEDE2000 in the objective function. This is done
  spectrally — we compute the full predicted spectrum, convert to LAB, and
  compute ΔE*₀₀ at each iteration.

Assumptions:
  - Complete hiding (opaque ink film)
  - No interaction effects between colorants
  - Linear concentration-K/S relationship (Beer-Lambert for K/S)
  - Substrate K/S is known (white base measurement)
  - All bases are from the same ink series

Limitations:
  - Does not account for metamerism
  - Does not optimize for cost
  - Single-constant K/S (no scattering coefficient separation)
  - Maximum ~12 bases per formula for optimizer stability
  - Fluorescent colorants not modeled

Future improvements:
  - Two-constant K/S with transmission data
  - Multi-start optimization to avoid local minima
  - Cost-weighted objective function
  - Genetic algorithm for large base sets
  - Saunderson correction for surface reflections
"""

import logging
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize

from app.services.color_science import (
    NUM_WAVELENGTHS,
    reflectance_to_ks,
    ks_to_reflectance,
    spectral_to_lab,
    delta_e_76,
    delta_e_2000,
    two_constant_km_over_substrate,
    metamerism_index,
)

logger = logging.getLogger(__name__)

# Maximum number of bases to include in a single formula.
# More than this makes the optimizer slow and results unreliable.
MAX_BASES_PER_FORMULA = 12

# Minimum concentration for a component to be included in final formula.
# Below this threshold, the component is treated as zero.
MIN_CONCENTRATION_THRESHOLD = 0.001  # 0.1%

# Default batch size for weight calculations (grams)
DEFAULT_BATCH_SIZE = 1000.0


@dataclass
class ColorantData:
    """Pre-processed colorant data for formulation.

    Attributes:
        base_id: Database ID of the mixing base.
        code: Base code/identifier.
        name: Base name.
        ks_spectrum: K/S spectrum of the colorant (substrate-corrected).
        concentration_pct: Concentration at which the K/S data was measured.
        cost_per_kg: Cost per kilogram (optional, for cost optimization).
        k_spectrum: Absorption coefficient array for two-constant K-M (optional).
        s_spectrum: Scattering coefficient array for two-constant K-M (optional).
    """
    base_id: int
    code: str
    name: str
    ks_spectrum: np.ndarray  # Shape: (43,)
    concentration_pct: float
    cost_per_kg: float = 0.0
    k_spectrum: np.ndarray = None
    s_spectrum: np.ndarray = None


@dataclass
class FormulaComponent:
    """A single component in a generated formula."""
    base_id: int
    code: str
    name: str
    percentage: float  # Weight percentage (0-100)
    weight_grams: float  # Weight for default batch size


@dataclass
class FormulationResult:
    """Result of a formulation optimization."""
    success: bool
    components: list[FormulaComponent] = field(default_factory=list)
    predicted_reflectance: np.ndarray = field(default_factory=lambda: np.array([]))
    predicted_lab: tuple = (0.0, 0.0, 0.0)
    target_lab: tuple = (0.0, 0.0, 0.0)
    delta_e_76: float = 0.0
    delta_e_2000: float = 0.0
    iterations: int = 0
    error_message: str = ''
    total_cost_per_kg: float = 0.0
    metamerism: dict = field(default_factory=dict)


class FormulationEngine:
    """Core formulation engine.

    Usage:
        engine = FormulationEngine()

        # Prepare colorant data
        substrate_ks = reflectance_to_ks(substrate_reflectance)
        colorants = []
        for base in bases:
            ks = reflectance_to_ks(base.reflectance) - substrate_ks
            colorants.append(ColorantData(
                base_id=base.id, code=base.code, name=base.name,
                ks_spectrum=ks, concentration_pct=100.0
            ))

        # Run formulation
        result = engine.formulate(
            target_reflectance=target_spectrum,
            colorants=colorants,
            substrate_ks=substrate_ks
        )
    """

    def __init__(self, batch_size: float = DEFAULT_BATCH_SIZE,
                 max_bases: int = MAX_BASES_PER_FORMULA,
                 formulation_mode: str = 'opaque',
                 film_thickness: float = 1.0,
                 cost_weight: float = 0.0):
        """
        Args:
            batch_size: Default batch size in grams.
            max_bases: Maximum colorants per formula.
            formulation_mode: 'opaque' (litho, single-constant K-M) or
                              'translucent' (flexo, two-constant K-M).
            film_thickness: Relative film thickness for translucent mode.
            cost_weight: Weight for cost in objective (0=ignore, 0.1=light, 0.5=heavy).
                         Final objective = dE2000 + cost_weight * normalized_cost.
        """
        self.batch_size = batch_size
        self.max_bases = max_bases
        self.formulation_mode = formulation_mode
        self.film_thickness = film_thickness
        self.cost_weight = cost_weight

    def formulate(
        self,
        target_reflectance: np.ndarray = None,
        target_lab: tuple = None,
        colorants: list[ColorantData] = None,
        substrate_ks: np.ndarray = None,
        substrate_reflectance: np.ndarray = None,
        max_components: int = None,
    ) -> FormulationResult:
        """Generate an optimal formula to match a target color.

        Either target_reflectance or target_lab must be provided.
        If only target_lab is provided, optimization is done in LAB space directly.
        If target_reflectance is provided, spectral matching is used (preferred).

        Args:
            target_reflectance: Target spectral reflectance (43 values, 360-780nm).
            target_lab: Target CIELAB values (L*, a*, b*) — used if no spectral data.
            colorants: List of available colorants with K/S data.
            substrate_ks: K/S spectrum of the substrate/white base (opaque mode).
            substrate_reflectance: Substrate reflectance array (translucent mode).
            max_components: Max number of colorants in formula (default: self.max_bases).

        Returns:
            FormulationResult with the optimized formula.
        """
        if colorants is None or len(colorants) == 0:
            return FormulationResult(
                success=False,
                error_message='No colorants provided for formulation.'
            )

        if substrate_ks is None:
            substrate_ks = reflectance_to_ks(np.full(NUM_WAVELENGTHS, 0.9))
            logger.warning('No substrate K/S provided, using default white substrate')

        if substrate_reflectance is None:
            substrate_reflectance = np.full(NUM_WAVELENGTHS, 0.9)

        max_components = max_components or self.max_bases
        use_two_constant = (self.formulation_mode == 'translucent')

        # Check if two-constant data is available for translucent mode
        if use_two_constant:
            has_two_constant = all(
                c.k_spectrum is not None and c.s_spectrum is not None
                for c in colorants
            )
            if not has_two_constant:
                logger.warning('Two-constant K/S data not available, falling back to opaque mode')
                use_two_constant = False

        # Determine target
        if target_reflectance is not None:
            target_reflectance = np.asarray(target_reflectance, dtype=float)
            target_lab_computed = spectral_to_lab(target_reflectance)
            target_ks = reflectance_to_ks(target_reflectance)
        elif target_lab is not None:
            target_lab_computed = target_lab
            target_ks = None
        else:
            return FormulationResult(
                success=False,
                error_message='Either target_reflectance or target_lab must be provided.'
            )

        # Pre-select most relevant colorants if we have too many
        if len(colorants) > max_components:
            colorants = self._preselect_colorants(
                colorants, target_lab_computed, substrate_ks, max_components
            )

        n = len(colorants)

        # Build matrices
        ks_matrix = np.column_stack([c.ks_spectrum for c in colorants])
        costs = np.array([c.cost_per_kg for c in colorants])
        max_cost = np.max(costs) if np.any(costs > 0) else 1.0

        if use_two_constant:
            k_matrix = np.column_stack([c.k_spectrum for c in colorants])
            s_matrix = np.column_stack([c.s_spectrum for c in colorants])
            sub_R = np.asarray(substrate_reflectance, dtype=float)

        # Objective function
        def objective(concentrations):
            if use_two_constant:
                K_mix = k_matrix @ concentrations
                S_mix = s_matrix @ concentrations
                predicted_R = two_constant_km_over_substrate(
                    K_mix, S_mix, sub_R, self.film_thickness
                )
            else:
                predicted_ks = substrate_ks + ks_matrix @ concentrations
                predicted_R = ks_to_reflectance(predicted_ks)

            predicted_lab = spectral_to_lab(predicted_R)
            de = delta_e_2000(target_lab_computed, predicted_lab)

            # Cost penalty
            if self.cost_weight > 0 and max_cost > 0:
                cost = np.dot(concentrations, costs) / max_cost
                return de + self.cost_weight * cost
            return de

        # Constraints: concentrations sum to 1.0
        constraints = [{'type': 'eq', 'fun': lambda c: np.sum(c) - 1.0}]
        bounds = [(0.0, 1.0)] * n
        x0 = np.ones(n) / n

        # Try a smarter initial guess based on spectral similarity
        if target_ks is not None and not use_two_constant:
            x0_smart = self._smart_initial_guess(ks_matrix, target_ks - substrate_ks, n)
            if x0_smart is not None:
                try:
                    result_equal = minimize(
                        objective, x0, method='SLSQP',
                        bounds=bounds, constraints=constraints,
                        options={'maxiter': 200, 'ftol': 1e-10}
                    )
                    result_smart = minimize(
                        objective, x0_smart, method='SLSQP',
                        bounds=bounds, constraints=constraints,
                        options={'maxiter': 200, 'ftol': 1e-10}
                    )
                    if result_smart.fun < result_equal.fun:
                        opt_result = result_smart
                    else:
                        opt_result = result_equal
                except Exception:
                    opt_result = minimize(
                        objective, x0, method='SLSQP',
                        bounds=bounds, constraints=constraints,
                        options={'maxiter': 500, 'ftol': 1e-10}
                    )
            else:
                opt_result = minimize(
                    objective, x0, method='SLSQP',
                    bounds=bounds, constraints=constraints,
                    options={'maxiter': 500, 'ftol': 1e-10}
                )
        else:
            opt_result = minimize(
                objective, x0, method='SLSQP',
                bounds=bounds, constraints=constraints,
                options={'maxiter': 500, 'ftol': 1e-10}
            )

        # Build result
        concentrations = opt_result.x

        # Filter out negligible components
        components = []
        for i, conc in enumerate(concentrations):
            if conc >= MIN_CONCENTRATION_THRESHOLD:
                components.append(FormulaComponent(
                    base_id=colorants[i].base_id,
                    code=colorants[i].code,
                    name=colorants[i].name,
                    percentage=round(conc * 100.0, 4),
                    weight_grams=round(conc * self.batch_size, 2),
                ))

        # Normalize percentages to sum to 100% after filtering
        total_pct = sum(c.percentage for c in components)
        if total_pct > 0 and abs(total_pct - 100.0) > 0.01:
            scale = 100.0 / total_pct
            for c in components:
                c.percentage = round(c.percentage * scale, 4)
                c.weight_grams = round(c.percentage / 100.0 * self.batch_size, 2)

        components.sort(key=lambda c: c.percentage, reverse=True)

        # Calculate predicted color
        if use_two_constant:
            K_mix = k_matrix @ concentrations
            S_mix = s_matrix @ concentrations
            predicted_R = two_constant_km_over_substrate(
                K_mix, S_mix, sub_R, self.film_thickness
            )
        else:
            predicted_ks = substrate_ks + ks_matrix @ concentrations
            predicted_R = ks_to_reflectance(predicted_ks)

        predicted_lab = spectral_to_lab(predicted_R)
        de76 = delta_e_76(target_lab_computed, predicted_lab)
        de2000 = delta_e_2000(target_lab_computed, predicted_lab)

        # Calculate total cost per kg
        total_cost = float(np.dot(concentrations, costs))

        # Compute metamerism index if we have spectral data
        met = {}
        if target_reflectance is not None and len(predicted_R) == NUM_WAVELENGTHS:
            try:
                met = metamerism_index(target_reflectance, predicted_R)
            except Exception:
                pass

        return FormulationResult(
            success=True,
            components=components,
            predicted_reflectance=predicted_R,
            predicted_lab=predicted_lab,
            target_lab=target_lab_computed,
            delta_e_76=round(de76, 4),
            delta_e_2000=round(de2000, 4),
            iterations=opt_result.nit if hasattr(opt_result, 'nit') else 0,
            total_cost_per_kg=round(total_cost, 2),
            metamerism=met,
        )

    def formulate_multi(
        self,
        target_reflectance: np.ndarray = None,
        target_lab: tuple = None,
        colorants: list[ColorantData] = None,
        substrate_ks: np.ndarray = None,
        substrate_reflectance: np.ndarray = None,
        num_results: int = 3,
    ) -> list[FormulationResult]:
        """Generate multiple formula alternatives.

        Uses different subsets of colorants to produce diverse results.
        Returns results sorted by delta_e_2000.
        """
        results = []

        # First, try with all colorants
        result = self.formulate(
            target_reflectance=target_reflectance,
            target_lab=target_lab,
            colorants=colorants,
            substrate_ks=substrate_ks,
            substrate_reflectance=substrate_reflectance,
        )
        if result.success:
            results.append(result)

        # Try with subsets: remove each colorant one at a time and re-optimize
        if colorants and len(colorants) > 2:
            for i in range(len(colorants)):
                if len(results) >= num_results:
                    break
                subset = [c for j, c in enumerate(colorants) if j != i]
                result = self.formulate(
                    target_reflectance=target_reflectance,
                    target_lab=target_lab,
                    colorants=subset,
                    substrate_ks=substrate_ks,
                    substrate_reflectance=substrate_reflectance,
                )
                if result.success:
                    is_different = all(
                        abs(result.delta_e_2000 - r.delta_e_2000) > 0.1
                        for r in results
                    )
                    if is_different:
                        results.append(result)

        results.sort(key=lambda r: r.delta_e_2000)
        return results[:num_results]

    def _preselect_colorants(
        self,
        colorants: list[ColorantData],
        target_lab: tuple,
        substrate_ks: np.ndarray,
        max_count: int,
    ) -> list[ColorantData]:
        """Pre-select the most relevant colorants for the target color.

        Uses a heuristic: compute each colorant's predicted color at 100%
        concentration and select those closest to the target in LAB space.
        Always includes the white/transparent base if present.
        """
        scores = []
        for i, c in enumerate(colorants):
            predicted_ks = substrate_ks + c.ks_spectrum
            predicted_R = ks_to_reflectance(predicted_ks)
            predicted_lab = spectral_to_lab(predicted_R)
            de = delta_e_2000(target_lab, predicted_lab)
            scores.append((de, i))

        scores.sort()
        selected_indices = [idx for _, idx in scores[:max_count]]
        return [colorants[i] for i in selected_indices]

    def _smart_initial_guess(
        self,
        ks_matrix: np.ndarray,
        target_ks_delta: np.ndarray,
        n: int,
    ) -> np.ndarray:
        """Generate a smarter initial guess using non-negative least squares.

        Solves: min ||ks_matrix @ c - target_ks_delta||²  subject to c >= 0
        Then normalizes so sum(c) = 1.
        """
        try:
            from scipy.optimize import nnls
            c, _ = nnls(ks_matrix, target_ks_delta)
            total = np.sum(c)
            if total > 0:
                c = c / total
                return c
        except Exception:
            pass
        return None
