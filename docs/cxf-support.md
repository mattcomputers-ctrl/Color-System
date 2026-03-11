# CXF File Support

## Supported Format

**CXF/X-4** (ISO 17972-4) — Color Exchange Format for spectral data.

This is the most widely used CXF variant in the ink and printing industry.

## Supported Elements

The parser extracts the following data from CXF files:

| Element | Description | Required |
|---------|-------------|----------|
| `Object/@Name` | Color name/identifier | No |
| `ReflectanceSpectrum` | Spectral reflectance values | Yes* |
| `ReflectanceSpectrum/@StartWL` | Start wavelength (nm) | Default: 360 |
| `ReflectanceSpectrum/@EndWL` | End wavelength (nm) | Default: 780 |
| `ReflectanceSpectrum/@Interval` | Wavelength interval (nm) | Default: 10 |
| `ColorCIELab/L`, `A`, `B` | CIELAB values | No* |

\* At least one of spectral data or LAB values must be present.

## Supported Variations

- **With namespace**: `xmlns="http://colorexchangeformat.com/CxF3-core"`
- **Without namespace**: Legacy files without XML namespaces
- **Value separators**: Space-separated, comma-separated, or semicolon-separated
- **Multiple objects**: Only the first color object is used by default
- **Alternate element names**: `SpectralData`, `Spectrum`, `ColorSpectrum`, `ReflectanceData`
- **Alternate attribute names**: `StartWavelength`, `WavelengthStart`, `startWL`, etc.

## Wavelength Normalization

If the source file has a different wavelength range or interval than the
system standard (360-780nm, 10nm), the parser will:

1. Linearly interpolate values to match 360-780nm at 10nm intervals
2. Clamp values to the 0.0-2.0 range
3. Warn if extrapolation is required (source range doesn't cover target range)

## Example CXF File

```xml
<?xml version="1.0" encoding="UTF-8"?>
<CxF xmlns="http://colorexchangeformat.com/CxF3-core">
  <Resources>
    <ObjectCollection>
      <Object Name="Sample Red">
        <ReflectanceSpectrum StartWL="360" EndWL="780" Interval="10">
          0.0523 0.0498 0.0487 0.0472 0.0461 0.0455 0.0448 0.0443
          0.0439 0.0436 0.0434 0.0432 0.0431 0.0430 0.0429 0.0428
          0.0428 0.0428 0.0429 0.0432 0.0438 0.0452 0.0489 0.0587
          0.0823 0.1328 0.2189 0.3391 0.4612 0.5498 0.6012 0.6312
          0.6498 0.6612 0.6698 0.6756 0.6798 0.6828 0.6851 0.6869
          0.6883 0.6895 0.6905
        </ReflectanceSpectrum>
        <ColorCIELab>
          <L>42.51</L>
          <A>58.73</A>
          <B>31.22</B>
        </ColorCIELab>
      </Object>
    </ObjectCollection>
  </Resources>
</CxF>
```

## Unsupported Features

The following CXF features are **not currently supported**:

- Transmittance spectra
- Emittance spectra
- Multi-angle / goniospectrophotometric data
- Fluorescence data
- Density values
- Color difference specifications
- ICC profiles embedded in CXF
- CxF/X-1, CxF/X-2, CxF/X-3 variants
- Nested resources / complex object hierarchies

## Adding Support for New Formats

The parser is modular. To add support for a new CXF variant:

1. Create a new parser class in `app/services/`
2. Implement the same interface as `CxfParser` (`parse_file`, `parse_bytes`)
3. Register it in the file upload handler with a format identifier
4. The `CxfParseResult` and `ParsedColor` data classes are shared across parsers
