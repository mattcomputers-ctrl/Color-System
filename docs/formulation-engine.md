# Formulation Engine

## Mathematical Model

The formulation engine uses **Kubelka-Munk single-constant theory** to predict
the color of pigment mixtures and optimize formulas.

### Kubelka-Munk Function

For an opaque (completely hiding) layer, the relationship between reflectance
and the absorption/scattering coefficients is:

```
K/S = (1 - R)² / (2R)
```

Where:
- `R` = spectral reflectance factor (0 to 1)
- `K` = absorption coefficient
- `S` = scattering coefficient
- `K/S` = the ratio (single constant)

### Additive Mixing

K/S values are additive for mixtures:

```
(K/S)_mix = Σ cᵢ · (K/S)ᵢ
```

Where:
- `cᵢ` = concentration (weight fraction) of colorant i
- `(K/S)ᵢ` = K/S spectrum of colorant i at unit concentration

### Colorant K/S Derivation

Each colorant's net K/S is derived by subtracting the substrate contribution:

```
(K/S)_colorant = (K/S)_measured - (K/S)_substrate
```

The substrate is typically the white/transparent base measured as a drawdown.

### Predicted Reflectance

The predicted reflectance of the mixture is the inverse K-M function:

```
R = 1 + (K/S) - √((K/S)² + 2·(K/S))
```

### Optimization

The optimizer minimizes **CIEDE2000** color difference between the predicted
and target colors:

```
minimize  ΔE*₀₀(LAB_predicted, LAB_target)
subject to:
  Σ cᵢ = 1.0     (concentrations sum to 100%)
  cᵢ ≥ 0          (no negative concentrations)
```

We use `scipy.optimize.minimize` with the **SLSQP** method, which handles
both equality and inequality constraints efficiently.

### Initial Guess Strategy

1. **Equal parts**: Start with equal concentrations for all bases
2. **NNLS (Non-Negative Least Squares)**: Solve `K·c ≈ target_K/S` as a
   least-squares problem to get a spectral starting point
3. Both are tried; the one producing lower ΔE is used as the starting point

## Color Difference Metrics

### CIEDE2000 (Primary)

The CIEDE2000 formula is used as the primary quality metric. It correlates
better with human perception than CIE76, especially for:
- Near-neutral colors
- Saturated blues
- Colors with high chroma differences

### CIE76 (Reference)

CIE76 (Euclidean distance in CIELAB) is also calculated for reference and
backward compatibility with older systems.

### Quality Thresholds

| ΔE*₀₀ | Assessment |
|--------|------------|
| < 0.5  | Imperceptible |
| < 1.0  | Excellent match |
| < 2.0  | Acceptable for most applications |
| < 3.5  | Visible but may be acceptable |
| ≥ 3.5  | Unacceptable for critical color |

## Assumptions

1. **Complete hiding**: The ink film is opaque enough that the substrate
   color doesn't show through. For transparent inks, this assumption
   is less valid.

2. **No interaction effects**: Colorants don't chemically interact with
   each other. This is generally true for well-formulated ink systems
   but can break down with certain pigment combinations.

3. **Linear K/S-concentration relationship**: K/S scales linearly with
   concentration. This holds well for low-to-moderate concentrations
   but may deviate at very high pigment loadings.

4. **Measurement conditions**: All spectral data should be measured under
   the same geometry (typically d/8° or 45°/0°) and conditions.

5. **D50 illuminant**: All LAB calculations use CIE D50 illuminant with
   2° standard observer, which is the ISO standard for graphic arts.

## Limitations

1. **Single-constant K/S**: The system uses K/S ratio, not separate K and
   S values. This is adequate for opaque systems but limits accuracy for
   translucent or transparent ink films.

2. **No Saunderson correction**: Surface reflections at the air-ink
   interface are not modeled. This can cause systematic errors,
   especially for glossy surfaces.

3. **No metamerism detection**: The system doesn't warn if two colors
   match under one illuminant but not another.

4. **Local minima**: The SLSQP optimizer may find a local minimum rather
   than the global optimum. Multi-start optimization would improve this.

5. **Maximum bases**: Optimization becomes unreliable with more than ~12
   bases per formula. Pre-selection heuristics are used for larger base sets.

## Improvement Roadmap

### Near-term
- Multi-start optimization (random restarts)
- Saunderson correction for surface reflections
- Cost-weighted optimization (minimize expensive pigments)

### Medium-term
- Two-constant Kubelka-Munk (requires transmission measurements)
- Metamerism index calculation
- Gamut boundary visualization

### Long-term
- Neural network–assisted formulation
- Genetic algorithm for large colorant sets
- Multi-substrate optimization
- Aging/weathering prediction
