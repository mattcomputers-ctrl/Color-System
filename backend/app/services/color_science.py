"""Color science utility functions.

Implements core color math operations needed by the formulation engine:
  - Spectral to XYZ tristimulus conversion
  - XYZ to CIELAB conversion
  - CIEDE2000 color difference calculation
  - Kubelka-Munk K/S calculation from reflectance

All spectral calculations use:
  - CIE D50 illuminant (standard for graphic arts / printing)
  - CIE 2° standard observer
  - Wavelength range 360-780nm at 10nm intervals (43 data points)

References:
  - CIE 15:2004 (Colorimetry)
  - ASTM E308 (Standard Practice for Computing Colors of Objects)
  - Kubelka, P. and Munk, F. (1931), Z. Tech. Phys., 12, 593
"""

import numpy as np

# Standard wavelengths: 360-780nm at 10nm intervals
WAVELENGTHS = np.arange(360, 781, 10, dtype=float)
NUM_WAVELENGTHS = len(WAVELENGTHS)  # 43

# CIE 2° Standard Observer color matching functions (360-780nm, 10nm interval)
# Source: CIE 15:2004 Table T.2
# fmt: off
CMF_X = np.array([
    0.0001, 0.0002, 0.0004, 0.0015, 0.0045, 0.0105, 0.0201, 0.0362,
    0.0679, 0.1102, 0.1655, 0.2257, 0.2904, 0.3597, 0.4334, 0.5121,
    0.5945, 0.6784, 0.7621, 0.8425, 0.9163, 0.9786, 1.0263, 1.0567,
    1.0622, 1.0456, 1.0026, 0.9384, 0.8544, 0.7514, 0.6424, 0.5419,
    0.4479, 0.3608, 0.2835, 0.2187, 0.1649, 0.1212, 0.0874, 0.0636,
    0.0468, 0.0329, 0.0227
])

CMF_Y = np.array([
    0.0000, 0.0001, 0.0001, 0.0004, 0.0012, 0.0040, 0.0073, 0.0116,
    0.0218, 0.0350, 0.0536, 0.0816, 0.1327, 0.2072, 0.3230, 0.5030,
    0.7100, 0.8620, 0.9540, 0.9950, 0.9950, 0.9520, 0.8700, 0.7570,
    0.6310, 0.5030, 0.3810, 0.2650, 0.1750, 0.1070, 0.0610, 0.0320,
    0.0170, 0.0082, 0.0041, 0.0021, 0.0010, 0.0005, 0.0003, 0.0002,
    0.0001, 0.0001, 0.0000
])

CMF_Z = np.array([
    0.0007, 0.0011, 0.0020, 0.0072, 0.0225, 0.0514, 0.1006, 0.1852,
    0.3502, 0.5688, 0.8563, 1.1322, 1.4146, 1.6866, 1.9282, 2.0205,
    1.9485, 1.7377, 1.4525, 1.1428, 0.8369, 0.5723, 0.3625, 0.2129,
    0.1176, 0.0601, 0.0281, 0.0122, 0.0053, 0.0020, 0.0008, 0.0003,
    0.0002, 0.0001, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
    0.0000, 0.0000, 0.0000
])

# CIE D50 illuminant SPD (360-780nm, 10nm interval)
# Source: CIE 15:2004
D50_SPD = np.array([
    24.49, 27.18, 32.00, 39.43, 47.84, 55.32, 63.07, 71.90,
    80.01, 89.40, 92.25, 96.53, 96.19, 97.34, 99.19, 100.00,
    101.28, 99.06, 98.74, 96.01, 96.54, 96.72, 96.11, 92.10,
    89.74, 89.49, 90.43, 90.06, 85.95, 86.69, 86.60, 84.87,
    82.52, 78.23, 74.67, 68.74, 67.95, 65.20, 63.55, 60.00,
    57.06, 54.82, 52.57
])
# fmt: on

# D50 reference white point (XYZ values for perfect diffuser under D50)
# Pre-calculated as sum(D50_SPD * CMF_x) etc., normalized so Y=100
_k = 100.0 / np.sum(D50_SPD * CMF_Y)
D50_XN = np.sum(D50_SPD * CMF_X) * _k
D50_YN = 100.0  # By definition
D50_ZN = np.sum(D50_SPD * CMF_Z) * _k


def spectral_to_xyz(reflectance: np.ndarray) -> tuple[float, float, float]:
    """Convert spectral reflectance to CIE XYZ tristimulus values.

    Args:
        reflectance: Array of 43 reflectance values (360-780nm, 10nm interval).
                     Values should be in 0-1 range (reflectance factor).

    Returns:
        Tuple of (X, Y, Z) tristimulus values.
    """
    reflectance = np.asarray(reflectance, dtype=float)
    assert len(reflectance) == NUM_WAVELENGTHS, \
        f'Expected {NUM_WAVELENGTHS} values, got {len(reflectance)}'

    k = 100.0 / np.sum(D50_SPD * CMF_Y)
    X = k * np.sum(D50_SPD * reflectance * CMF_X)
    Y = k * np.sum(D50_SPD * reflectance * CMF_Y)
    Z = k * np.sum(D50_SPD * reflectance * CMF_Z)
    return (X, Y, Z)


def xyz_to_lab(X: float, Y: float, Z: float,
               Xn: float = D50_XN, Yn: float = D50_YN, Zn: float = D50_ZN
               ) -> tuple[float, float, float]:
    """Convert CIE XYZ to CIELAB.

    Args:
        X, Y, Z: Tristimulus values.
        Xn, Yn, Zn: Reference white point (default D50).

    Returns:
        Tuple of (L*, a*, b*).
    """
    def f(t):
        delta = 6.0 / 29.0
        if t > delta ** 3:
            return t ** (1.0 / 3.0)
        else:
            return t / (3.0 * delta ** 2) + 4.0 / 29.0

    fx = f(X / Xn)
    fy = f(Y / Yn)
    fz = f(Z / Zn)

    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return (L, a, b)


def spectral_to_lab(reflectance: np.ndarray) -> tuple[float, float, float]:
    """Convert spectral reflectance directly to CIELAB."""
    X, Y, Z = spectral_to_xyz(reflectance)
    return xyz_to_lab(X, Y, Z)


def delta_e_76(lab1: tuple, lab2: tuple) -> float:
    """CIE76 color difference (Euclidean distance in CIELAB)."""
    dL = lab1[0] - lab2[0]
    da = lab1[1] - lab2[1]
    db = lab1[2] - lab2[2]
    return np.sqrt(dL**2 + da**2 + db**2)


def delta_e_2000(lab1: tuple, lab2: tuple) -> float:
    """CIEDE2000 color difference.

    Implementation follows the formulae in:
    Sharma, G., Wu, W., Dalal, E.N. (2005).
    "The CIEDE2000 color-difference formula: Implementation notes,
     supplementary test data, and mathematical observations."
    Color Research & Application, 30(1), 21-30.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    # Step 1: Calculate C' and h'
    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    C_avg = (C1 + C2) / 2.0
    C_avg_7 = C_avg**7
    G = 0.5 * (1.0 - np.sqrt(C_avg_7 / (C_avg_7 + 25.0**7)))

    a1p = a1 * (1.0 + G)
    a2p = a2 * (1.0 + G)

    C1p = np.sqrt(a1p**2 + b1**2)
    C2p = np.sqrt(a2p**2 + b2**2)

    h1p = np.degrees(np.arctan2(b1, a1p)) % 360.0
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360.0

    # Step 2: Calculate delta values
    dLp = L2 - L1
    dCp = C2p - C1p

    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180.0:
        dhp = h2p - h1p
    elif h2p - h1p > 180.0:
        dhp = h2p - h1p - 360.0
    else:
        dhp = h2p - h1p + 360.0

    dHp = 2.0 * np.sqrt(C1p * C2p) * np.sin(np.radians(dhp / 2.0))

    # Step 3: Calculate CIEDE2000
    Lp_avg = (L1 + L2) / 2.0
    Cp_avg = (C1p + C2p) / 2.0

    if C1p * C2p == 0:
        hp_avg = h1p + h2p
    elif abs(h1p - h2p) <= 180.0:
        hp_avg = (h1p + h2p) / 2.0
    elif h1p + h2p < 360.0:
        hp_avg = (h1p + h2p + 360.0) / 2.0
    else:
        hp_avg = (h1p + h2p - 360.0) / 2.0

    T = (1.0
         - 0.17 * np.cos(np.radians(hp_avg - 30.0))
         + 0.24 * np.cos(np.radians(2.0 * hp_avg))
         + 0.32 * np.cos(np.radians(3.0 * hp_avg + 6.0))
         - 0.20 * np.cos(np.radians(4.0 * hp_avg - 63.0)))

    SL = 1.0 + 0.015 * (Lp_avg - 50.0)**2 / np.sqrt(20.0 + (Lp_avg - 50.0)**2)
    SC = 1.0 + 0.045 * Cp_avg
    SH = 1.0 + 0.015 * Cp_avg * T

    Cp_avg_7 = Cp_avg**7
    RC = 2.0 * np.sqrt(Cp_avg_7 / (Cp_avg_7 + 25.0**7))
    d_theta = 30.0 * np.exp(-((hp_avg - 275.0) / 25.0)**2)
    RT = -np.sin(np.radians(2.0 * d_theta)) * RC

    dE = np.sqrt(
        (dLp / SL)**2 +
        (dCp / SC)**2 +
        (dHp / SH)**2 +
        RT * (dCp / SC) * (dHp / SH)
    )
    return float(dE)


# CIE D65 illuminant SPD (360-780nm, 10nm interval) — display/general use
# Source: CIE 15:2004
# fmt: off
D65_SPD = np.array([
    38.68, 44.87, 54.65, 68.70, 82.75, 87.12, 91.49, 92.46,
    93.43, 99.54, 95.59, 104.86, 104.59, 105.08, 104.36, 100.00,
    96.33, 95.79, 88.69, 90.01, 89.60, 87.70, 83.29, 83.70,
    80.03, 80.21, 82.28, 78.28, 74.00, 69.72, 70.67, 68.36,
    66.09, 65.10, 63.38, 62.44, 59.47, 56.61, 57.33, 54.92,
    52.62, 58.27, 60.28
])

# CIE Illuminant A SPD (360-780nm, 10nm interval) — tungsten/incandescent
# Source: CIE 15:2004
A_SPD = np.array([
    6.14, 7.19, 8.42, 9.84, 11.45, 13.28, 15.34, 17.64,
    20.22, 23.07, 26.22, 29.68, 33.47, 37.60, 42.09, 46.94,
    52.18, 57.80, 63.82, 70.24, 77.07, 84.33, 92.01, 100.12,
    108.66, 117.64, 127.05, 136.91, 147.20, 157.93, 169.10, 180.71,
    192.75, 205.22, 218.12, 231.44, 245.18, 259.33, 273.89, 288.84,
    304.19, 319.93, 336.05
])
# fmt: on

# Pre-compute D65 and A white points
_k65 = 100.0 / np.sum(D65_SPD * CMF_Y)
D65_XN = np.sum(D65_SPD * CMF_X) * _k65
D65_YN = 100.0
D65_ZN = np.sum(D65_SPD * CMF_Z) * _k65

_kA = 100.0 / np.sum(A_SPD * CMF_Y)
A_XN = np.sum(A_SPD * CMF_X) * _kA
A_YN = 100.0
A_ZN = np.sum(A_SPD * CMF_Z) * _kA

# Illuminant registry for easy lookup
ILLUMINANTS = {
    'D50': {'spd': D50_SPD, 'Xn': D50_XN, 'Yn': D50_YN, 'Zn': D50_ZN},
    'D65': {'spd': D65_SPD, 'Xn': D65_XN, 'Yn': D65_YN, 'Zn': D65_ZN},
    'A':   {'spd': A_SPD,   'Xn': A_XN,   'Yn': A_YN,   'Zn': A_ZN},
}


def spectral_to_lab_illuminant(reflectance: np.ndarray, illuminant: str = 'D50') -> tuple:
    """Convert spectral reflectance to CIELAB under a specified illuminant."""
    ill = ILLUMINANTS[illuminant]
    r = np.asarray(reflectance, dtype=float)
    k = 100.0 / np.sum(ill['spd'] * CMF_Y)
    X = k * np.sum(ill['spd'] * r * CMF_X)
    Y = k * np.sum(ill['spd'] * r * CMF_Y)
    Z = k * np.sum(ill['spd'] * r * CMF_Z)
    return xyz_to_lab(X, Y, Z, ill['Xn'], ill['Yn'], ill['Zn'])


def metamerism_index(reflectance1: np.ndarray, reflectance2: np.ndarray,
                     illuminants: list = None) -> dict:
    """Compute metamerism index between two spectra across illuminants.

    Two colors may match under one illuminant but diverge under another.
    Returns dE00 under each illuminant pair.

    Args:
        reflectance1: First spectral reflectance (43 values).
        reflectance2: Second spectral reflectance (43 values).
        illuminants: List of illuminant names (default: D50, D65, A).

    Returns:
        Dict with 'illuminants' (per-illuminant dE00) and 'metamerism_risk' flag.
    """
    if illuminants is None:
        illuminants = ['D50', 'D65', 'A']

    results = {}
    for ill_name in illuminants:
        lab1 = spectral_to_lab_illuminant(reflectance1, ill_name)
        lab2 = spectral_to_lab_illuminant(reflectance2, ill_name)
        de = delta_e_2000(lab1, lab2)
        results[ill_name] = {
            'lab1': {'L': round(lab1[0], 2), 'a': round(lab1[1], 2), 'b': round(lab1[2], 2)},
            'lab2': {'L': round(lab2[0], 2), 'a': round(lab2[1], 2), 'b': round(lab2[2], 2)},
            'delta_e_2000': round(de, 4),
        }

    de_values = [v['delta_e_2000'] for v in results.values()]
    max_spread = max(de_values) - min(de_values) if len(de_values) > 1 else 0.0

    return {
        'illuminants': results,
        'max_spread': round(max_spread, 4),
        'metamerism_risk': 'high' if max_spread > 2.0 else 'moderate' if max_spread > 1.0 else 'low',
    }


def reflectance_to_ks(reflectance: np.ndarray) -> np.ndarray:
    """Convert reflectance to Kubelka-Munk K/S values (single-constant).

    K/S = (1 - R)² / (2R)

    Assumes complete hiding (opaque layer). Used for litho inks.
    For thin/transparent films (flexo), use two-constant theory.
    """
    R = np.asarray(reflectance, dtype=float)
    R = np.clip(R, 0.005, 0.995)
    return (1.0 - R) ** 2 / (2.0 * R)


def ks_to_reflectance(ks: np.ndarray) -> np.ndarray:
    """Convert K/S values back to reflectance.

    R = 1 + K/S - sqrt((K/S)² + 2·K/S)
    """
    ks = np.asarray(ks, dtype=float)
    ks = np.maximum(ks, 0.0)
    R = 1.0 + ks - np.sqrt(ks**2 + 2.0 * ks)
    return np.clip(R, 0.005, 0.995)


def two_constant_km_reflectance(K: np.ndarray, S: np.ndarray,
                                 film_thickness: float = 1.0) -> np.ndarray:
    """Two-constant Kubelka-Munk reflectance for translucent films.

    For thin ink films (flexo, gravure) where the substrate shows through,
    the single-constant theory is insufficient. This computes reflectance
    using separate absorption (K) and scattering (S) coefficients.

    R = (1 - R_inf²) / (e^(S·d·(1/R_inf - R_inf)) - R_inf²)

    where R_inf = 1 + K/S - sqrt((K/S)² + 2K/S) (infinite thickness reflectance)
    and d = film_thickness.

    For thick films (d → ∞), this converges to single-constant K/S.

    Args:
        K: Absorption coefficient array (43 wavelengths).
        S: Scattering coefficient array (43 wavelengths).
        film_thickness: Relative film thickness (1.0 = reference thickness).

    Returns:
        Reflectance array (43 values, 0-1 range).
    """
    K = np.asarray(K, dtype=float)
    S = np.asarray(S, dtype=float)
    S = np.maximum(S, 1e-10)  # avoid division by zero

    ks_ratio = K / S
    # R_inf is the reflectance at infinite thickness
    R_inf = 1.0 + ks_ratio - np.sqrt(ks_ratio**2 + 2.0 * ks_ratio)
    R_inf = np.clip(R_inf, 0.001, 0.999)

    a = S * film_thickness * (1.0 / R_inf - R_inf)
    # Clamp to prevent overflow in exp
    a = np.clip(a, -500, 500)

    R = (1.0 - R_inf**2) / (np.exp(a) - R_inf**2)
    return np.clip(R, 0.005, 0.995)


def two_constant_km_over_substrate(K: np.ndarray, S: np.ndarray,
                                    substrate_R: np.ndarray,
                                    film_thickness: float = 1.0) -> np.ndarray:
    """Two-constant K-M reflectance of a translucent film over a substrate.

    For flexo/gravure where the ink film is thin and the substrate affects
    the final appearance.

    R_total = R_film + T_film² * R_sub / (1 - R_film_internal * R_sub)

    This uses the simplified Kubelka-Munk hyperbolic solution for a finite
    layer backed by a substrate.

    Args:
        K: Absorption coefficient array (43 wavelengths).
        S: Scattering coefficient array (43 wavelengths).
        substrate_R: Substrate reflectance array (43 values).
        film_thickness: Relative film thickness.

    Returns:
        Combined reflectance array (43 values).
    """
    K = np.asarray(K, dtype=float)
    S = np.asarray(S, dtype=float)
    substrate_R = np.asarray(substrate_R, dtype=float)
    S = np.maximum(S, 1e-10)

    ks_ratio = K / S
    a_km = 1.0 + ks_ratio  # Kubelka-Munk 'a' parameter
    b_km = np.sqrt(np.maximum(a_km**2 - 1.0, 0.0))  # 'b' parameter
    b_km = np.maximum(b_km, 1e-10)

    bSd = b_km * S * film_thickness
    bSd = np.clip(bSd, -500, 500)

    sinh_bSd = np.sinh(bSd)
    cosh_bSd = np.cosh(bSd)

    Rg = np.clip(substrate_R, 0.005, 0.995)

    denom = b_km * cosh_bSd + (a_km - Rg) * sinh_bSd
    denom = np.where(np.abs(denom) < 1e-10, 1e-10, denom)

    R = (Rg * (b_km * cosh_bSd - a_km * sinh_bSd) + sinh_bSd) / denom
    return np.clip(R, 0.005, 0.995)
