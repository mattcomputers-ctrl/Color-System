"""Color science utility functions.

Implements core color math operations needed by the formulation engine:
  - Spectral to XYZ tristimulus conversion
  - XYZ to CIELAB conversion
  - CIEDE2000 color difference calculation
  - Kubelka-Munk K/S calculation from reflectance
  - Multi-observer support (2° and 10° standard observers)
  - Measurement filter conditions (M0, M1, M2, M3) per ISO 13655

All spectral calculations use:
  - CIE D50 illuminant (standard for graphic arts / printing)
  - Wavelength range 360-780nm at 10nm intervals (43 data points)
  - Configurable observer (2° or 10°) and measurement filter

Observers:
  - 2°  (CIE 1931) — standard for small field (<4°), traditional colorimetry
  - 10° (CIE 1964) — supplementary for larger field (>4°), better for large patches

Measurement Filters (ISO 13655):
  - M0: No UV filtering (includes all UV in source). Legacy/uncontrolled.
  - M1: D50 illuminant with defined UV content. Standard for graphic arts.
  - M2: UV-excluded (420nm cut). For measuring without UV fluorescence.
  - M3: Polarized measurement. For eliminating first-surface gloss.

References:
  - CIE 15:2004 (Colorimetry)
  - CIE 170-1:2006 (10° observer)
  - ISO 13655:2017 (Graphic technology — Spectral measurement conditions)
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

# CIE 10° Standard Observer color matching functions (360-780nm, 10nm interval)
# Source: CIE 15:2004 Table T.3 (CIE 1964 supplementary observer)
# Used for larger field stimuli (>4°), common in industrial color measurement.
# fmt: off
CMF_X_10 = np.array([
    0.0002, 0.0007, 0.0024, 0.0093, 0.0291, 0.0633, 0.1096, 0.1655,
    0.2257, 0.2904, 0.3391, 0.3954, 0.4608, 0.5314, 0.6067, 0.6857,
    0.7618, 0.8233, 0.8752, 0.9238, 0.9620, 0.9822, 0.9918, 0.9991,
    0.9973, 0.9824, 0.9556, 0.9152, 0.8689, 0.8256, 0.7774, 0.7204,
    0.6583, 0.5939, 0.5280, 0.4618, 0.3981, 0.3396, 0.2835, 0.2283,
    0.1798, 0.1402, 0.1076
])

CMF_Y_10 = np.array([
    0.0000, 0.0001, 0.0003, 0.0010, 0.0035, 0.0095, 0.0228, 0.0420,
    0.0668, 0.0988, 0.1344, 0.1789, 0.2458, 0.3400, 0.4622, 0.6075,
    0.7615, 0.8750, 0.9620, 1.0026, 1.0000, 0.9628, 0.8973, 0.8110,
    0.7097, 0.6027, 0.4959, 0.3916, 0.2952, 0.2129, 0.1470, 0.0993,
    0.0636, 0.0394, 0.0232, 0.0136, 0.0079, 0.0040, 0.0020, 0.0010,
    0.0005, 0.0003, 0.0001
])

CMF_Z_10 = np.array([
    0.0007, 0.0029, 0.0105, 0.0402, 0.1334, 0.2839, 0.5326, 0.7922,
    1.0582, 1.3176, 1.5281, 1.7412, 1.9693, 2.1633, 2.2726, 2.2487,
    2.1137, 1.8880, 1.5949, 1.2876, 0.9932, 0.7295, 0.5093, 0.3324,
    0.2043, 0.1187, 0.0651, 0.0332, 0.0159, 0.0074, 0.0033, 0.0015,
    0.0006, 0.0003, 0.0001, 0.0001, 0.0000, 0.0000, 0.0000, 0.0000,
    0.0000, 0.0000, 0.0000
])
# fmt: on

# Observer registry — maps observer name to its CMFs
OBSERVERS = {
    '2': {'x': CMF_X, 'y': CMF_Y, 'z': CMF_Z, 'label': 'CIE 2° (1931)'},
    '10': {'x': CMF_X_10, 'y': CMF_Y_10, 'z': CMF_Z_10, 'label': 'CIE 10° (1964)'},
}


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

# --- Measurement Filter Conditions (ISO 13655) ---
# These modify the effective illuminant SPD to simulate different measurement modes.

def _apply_m2_uv_cut(spd):
    """Apply M2 UV-excluded filter: zero out energy below 400nm.

    M2 measurements use a UV-cut filter (typically 400nm or 420nm cutoff)
    to eliminate UV-excited fluorescence. In practice this means the
    illuminant has no energy below ~400nm.
    """
    filtered = spd.copy()
    # Wavelengths: 360, 370, 380, 390 → indices 0,1,2,3
    filtered[0:4] = 0.0  # Zero below 400nm
    return filtered


def _apply_m3_polarized(spd):
    """Apply M3 polarized filter: reduce specular component.

    M3 uses cross-polarized measurement to remove first-surface (specular)
    reflection. The illuminant SPD itself is unchanged but the effective
    signal is reduced by the polarizer transmission (~40-45% loss).
    We model this as a uniform attenuation since the polarization effect
    is on the measurement geometry, not the illuminant spectrum shape.
    """
    # Polarization reduces total light by ~50% (crossed polarizers)
    # but the spectral shape remains the same. For colorimetric computation
    # the normalization factor k cancels this out, so M3 SPD = M1 SPD.
    # The real effect is on the measured reflectance (no gloss), not the
    # computation. We return unmodified SPD; the user supplies M3 reflectance.
    return spd.copy()


# Pre-compute M2 filtered D50 SPD
D50_M2_SPD = _apply_m2_uv_cut(D50_SPD)

# Measurement conditions registry
# M0 = no defined UV content (legacy, uses raw D50)
# M1 = D50 with defined UV content (standard for graphic arts; same as D50)
# M2 = UV-excluded (below 400nm zeroed)
# M3 = polarized (same SPD as M1; difference is in measured reflectance)
MEASUREMENT_FILTERS = {
    'M0': {'label': 'M0 — No UV control (legacy)', 'spd_modifier': None},
    'M1': {'label': 'M1 — D50 with UV (ISO 13655)', 'spd_modifier': None},
    'M2': {'label': 'M2 — UV excluded (400nm cut)', 'spd_modifier': _apply_m2_uv_cut},
    'M3': {'label': 'M3 — Polarized (no gloss)', 'spd_modifier': _apply_m3_polarized},
}


def _compute_white_point(spd, observer='2'):
    """Compute white point (Xn, Yn, Zn) for an SPD and observer."""
    obs = OBSERVERS[observer]
    k = 100.0 / np.sum(spd * obs['y'])
    Xn = np.sum(spd * obs['x']) * k
    Zn = np.sum(spd * obs['z']) * k
    return Xn, 100.0, Zn


# Illuminant registry for easy lookup (2° observer by default)
ILLUMINANTS = {
    'D50': {'spd': D50_SPD, 'Xn': D50_XN, 'Yn': D50_YN, 'Zn': D50_ZN},
    'D65': {'spd': D65_SPD, 'Xn': D65_XN, 'Yn': D65_YN, 'Zn': D65_ZN},
    'A':   {'spd': A_SPD,   'Xn': A_XN,   'Yn': A_YN,   'Zn': A_ZN},
}

# Pre-compute white points for 10° observer
_k_D50_10 = 100.0 / np.sum(D50_SPD * CMF_Y_10)
D50_XN_10 = np.sum(D50_SPD * CMF_X_10) * _k_D50_10
D50_ZN_10 = np.sum(D50_SPD * CMF_Z_10) * _k_D50_10

_k_D65_10 = 100.0 / np.sum(D65_SPD * CMF_Y_10)
D65_XN_10 = np.sum(D65_SPD * CMF_X_10) * _k_D65_10
D65_ZN_10 = np.sum(D65_SPD * CMF_Z_10) * _k_D65_10

_k_A_10 = 100.0 / np.sum(A_SPD * CMF_Y_10)
A_XN_10 = np.sum(A_SPD * CMF_X_10) * _k_A_10
A_ZN_10 = np.sum(A_SPD * CMF_Z_10) * _k_A_10

# Extended illuminant registry keyed by (illuminant, observer)
ILLUMINANTS_EXT = {
    ('D50', '2'):  {'spd': D50_SPD, 'Xn': D50_XN,    'Yn': 100.0, 'Zn': D50_ZN},
    ('D50', '10'): {'spd': D50_SPD, 'Xn': D50_XN_10, 'Yn': 100.0, 'Zn': D50_ZN_10},
    ('D65', '2'):  {'spd': D65_SPD, 'Xn': D65_XN,    'Yn': 100.0, 'Zn': D65_ZN},
    ('D65', '10'): {'spd': D65_SPD, 'Xn': D65_XN_10, 'Yn': 100.0, 'Zn': D65_ZN_10},
    ('A', '2'):    {'spd': A_SPD,   'Xn': A_XN,      'Yn': 100.0, 'Zn': A_ZN},
    ('A', '10'):   {'spd': A_SPD,   'Xn': A_XN_10,   'Yn': 100.0, 'Zn': A_ZN_10},
}


def spectral_to_lab_illuminant(reflectance: np.ndarray, illuminant: str = 'D50',
                                observer: str = '2', measurement_filter: str = None) -> tuple:
    """Convert spectral reflectance to CIELAB under specified conditions.

    Args:
        reflectance: Array of 43 reflectance values (360-780nm).
        illuminant: Illuminant name ('D50', 'D65', 'A').
        observer: Observer angle ('2' for 2°, '10' for 10°).
        measurement_filter: ISO 13655 filter ('M0', 'M1', 'M2', 'M3') or None.

    Returns:
        Tuple of (L*, a*, b*).
    """
    return spectral_to_lab_full(reflectance, illuminant, observer, measurement_filter)


def spectral_to_lab_full(reflectance: np.ndarray, illuminant: str = 'D50',
                          observer: str = '2', measurement_filter: str = None) -> tuple:
    """Full-featured spectral to CIELAB conversion.

    Supports all combinations of illuminant, observer, and measurement filter.

    Args:
        reflectance: Array of 43 reflectance values (360-780nm).
        illuminant: Illuminant name ('D50', 'D65', 'A').
        observer: Observer angle ('2' for 2°, '10' for 10°).
        measurement_filter: ISO 13655 filter ('M0', 'M1', 'M2', 'M3') or None.

    Returns:
        Tuple of (L*, a*, b*).
    """
    r = np.asarray(reflectance, dtype=float)
    obs = OBSERVERS[observer]

    # Get illuminant SPD
    key = (illuminant, observer)
    if key in ILLUMINANTS_EXT:
        ill = ILLUMINANTS_EXT[key]
    else:
        ill = ILLUMINANTS[illuminant]

    spd = ill['spd'].copy()

    # Apply measurement filter if specified
    if measurement_filter and measurement_filter in MEASUREMENT_FILTERS:
        modifier = MEASUREMENT_FILTERS[measurement_filter]['spd_modifier']
        if modifier is not None:
            spd = modifier(spd)
            # Recompute white point for the filtered SPD
            Xn, Yn, Zn = _compute_white_point(spd, observer)
            k = 100.0 / np.sum(spd * obs['y'])
            X = k * np.sum(spd * r * obs['x'])
            Y = k * np.sum(spd * r * obs['y'])
            Z = k * np.sum(spd * r * obs['z'])
            return xyz_to_lab(X, Y, Z, Xn, Yn, Zn)

    # Standard computation with pre-computed white points
    k = 100.0 / np.sum(spd * obs['y'])
    X = k * np.sum(spd * r * obs['x'])
    Y = k * np.sum(spd * r * obs['y'])
    Z = k * np.sum(spd * r * obs['z'])
    return xyz_to_lab(X, Y, Z, ill['Xn'], ill['Yn'], ill['Zn'])


def metamerism_index(reflectance1: np.ndarray, reflectance2: np.ndarray,
                     illuminants: list = None, observer: str = '2',
                     measurement_filter: str = None) -> dict:
    """Compute metamerism index between two spectra across illuminants.

    Two colors may match under one illuminant but diverge under another.
    Returns dE00 under each illuminant pair.

    Args:
        reflectance1: First spectral reflectance (43 values).
        reflectance2: Second spectral reflectance (43 values).
        illuminants: List of illuminant names (default: D50, D65, A).
        observer: Observer angle ('2' or '10').
        measurement_filter: ISO 13655 filter ('M0', 'M1', 'M2', 'M3') or None.

    Returns:
        Dict with 'illuminants' (per-illuminant dE00), 'metamerism_risk',
        'observer', and 'measurement_filter'.
    """
    if illuminants is None:
        illuminants = ['D50', 'D65', 'A']

    results = {}
    for ill_name in illuminants:
        lab1 = spectral_to_lab_full(reflectance1, ill_name, observer, measurement_filter)
        lab2 = spectral_to_lab_full(reflectance2, ill_name, observer, measurement_filter)
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
        'observer': observer,
        'measurement_filter': measurement_filter,
    }


def compute_lab_multi_condition(reflectance: np.ndarray,
                                 conditions: list = None) -> list:
    """Compute LAB values under multiple illuminant/observer/filter conditions.

    Useful for displaying a color's appearance under different viewing conditions.

    Args:
        reflectance: Array of 43 reflectance values.
        conditions: List of dicts, each with 'illuminant', 'observer', 'filter' keys.
                    Defaults to standard graphic arts conditions.

    Returns:
        List of dicts with condition info and computed LAB values.
    """
    if conditions is None:
        conditions = [
            {'illuminant': 'D50', 'observer': '2', 'filter': 'M1'},
            {'illuminant': 'D50', 'observer': '10', 'filter': 'M1'},
            {'illuminant': 'D50', 'observer': '2', 'filter': 'M2'},
            {'illuminant': 'D65', 'observer': '2', 'filter': None},
            {'illuminant': 'A', 'observer': '2', 'filter': None},
        ]

    results = []
    for cond in conditions:
        ill = cond.get('illuminant', 'D50')
        obs = cond.get('observer', '2')
        filt = cond.get('filter')
        lab = spectral_to_lab_full(reflectance, ill, obs, filt)
        obs_info = OBSERVERS.get(obs, {})
        filt_info = MEASUREMENT_FILTERS.get(filt, {}) if filt else {}
        results.append({
            'illuminant': ill,
            'observer': obs,
            'observer_label': obs_info.get('label', f'{obs}°'),
            'filter': filt,
            'filter_label': filt_info.get('label', filt or 'None'),
            'lab': {'L': round(lab[0], 2), 'a': round(lab[1], 2), 'b': round(lab[2], 2)},
        })
    return results


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
