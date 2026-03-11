"""CXF (Color Exchange Format) file parser.

Supported format: CXF/X-4 (ISO 17972-4)
This is the most common CXF variant used in the ink and printing industry.

CXF/X-4 files are XML documents containing spectral reflectance data.
The parser extracts:
  - Color name/identifier
  - Spectral reflectance values
  - Wavelength range and interval
  - CIELAB values (if present)
  - Illuminant and observer information

Architecture:
  The parser is modular — additional CXF schemas can be supported by adding
  new parser classes that implement the BaseCxfParser interface.

Known CXF namespaces handled:
  - http://colorexchangeformat.com/CxF3-core
  - http://colorexchangeformat.com/CxF3-spectral (not officially standard but used by some vendors)
  - No namespace (some legacy tools omit namespaces)

Limitations:
  - Only reflectance data is extracted (not transmittance or emittance)
  - Multi-angle (gonio) data is not supported
  - Only the first color object is used if multiple are present (configurable)
  - Fluorescence data is not extracted
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from lxml import etree

logger = logging.getLogger(__name__)

# Common CXF namespaces
CXF_NAMESPACES = {
    'cxf': 'http://colorexchangeformat.com/CxF3-core',
}


@dataclass
class SpectralData:
    """Parsed spectral data from a CXF file."""
    reflectance: list[float]
    wavelength_start: int = 360
    wavelength_end: int = 780
    wavelength_interval: int = 10

    @property
    def wavelengths(self) -> list[int]:
        return list(range(self.wavelength_start,
                          self.wavelength_end + 1,
                          self.wavelength_interval))

    @property
    def num_points(self) -> int:
        return len(self.reflectance)

    def validate(self) -> list[str]:
        errors = []
        expected = len(self.wavelengths)
        if len(self.reflectance) != expected:
            errors.append(
                f'Expected {expected} reflectance values for '
                f'{self.wavelength_start}-{self.wavelength_end}nm at {self.wavelength_interval}nm, '
                f'got {len(self.reflectance)}'
            )
        for i, v in enumerate(self.reflectance):
            if v < 0:
                errors.append(f'Negative reflectance value {v} at index {i}')
            if v > 2.0:
                errors.append(f'Reflectance value {v} at index {i} exceeds 2.0 (possible error)')
        return errors


@dataclass
class ParsedColor:
    """A single color object extracted from a CXF file."""
    name: str = ''
    spectral: Optional[SpectralData] = None
    lab_l: Optional[float] = None
    lab_a: Optional[float] = None
    lab_b: Optional[float] = None
    illuminant: str = 'D50'
    observer: str = '2'
    metadata: dict = field(default_factory=dict)

    @property
    def lab_values(self) -> Optional[dict]:
        if self.lab_l is not None:
            return {'L': self.lab_l, 'a': self.lab_a, 'b': self.lab_b}
        return None


@dataclass
class CxfParseResult:
    """Result of parsing a CXF file."""
    success: bool
    colors: list[ParsedColor] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_metadata: dict = field(default_factory=dict)

    @property
    def primary_color(self) -> Optional[ParsedColor]:
        """Return the first (or only) color in the file."""
        return self.colors[0] if self.colors else None


class CxfParser:
    """Main CXF parser supporting CXF/X-4 files.

    Usage:
        parser = CxfParser()
        result = parser.parse_file('/path/to/file.cxf')
        if result.success:
            color = result.primary_color
            reflectance = color.spectral.reflectance
    """

    # Target wavelength range for normalization
    TARGET_WL_START = 360
    TARGET_WL_END = 780
    TARGET_WL_INTERVAL = 10

    def parse_file(self, filepath: str) -> CxfParseResult:
        """Parse a CXF file from disk."""
        try:
            with open(filepath, 'rb') as f:
                return self.parse_bytes(f.read())
        except FileNotFoundError:
            return CxfParseResult(success=False, errors=[f'File not found: {filepath}'])
        except IOError as e:
            return CxfParseResult(success=False, errors=[f'Error reading file: {e}'])

    def parse_bytes(self, data: bytes) -> CxfParseResult:
        """Parse CXF data from bytes."""
        errors = []
        warnings = []

        try:
            root = etree.fromstring(data)
        except etree.XMLSyntaxError as e:
            return CxfParseResult(success=False, errors=[f'Invalid XML: {e}'])

        # Detect namespace
        ns = self._detect_namespace(root)

        # Extract file-level metadata
        file_metadata = self._extract_file_metadata(root, ns)

        # Find color objects
        colors = []
        color_elements = self._find_color_elements(root, ns)

        if not color_elements:
            return CxfParseResult(
                success=False,
                errors=['No color objects found in CXF file'],
                file_metadata=file_metadata,
            )

        for elem in color_elements:
            try:
                parsed = self._parse_color_element(elem, ns)
                if parsed:
                    # Validate spectral data
                    if parsed.spectral:
                        spec_errors = parsed.spectral.validate()
                        if spec_errors:
                            for e in spec_errors:
                                warnings.append(f'Color "{parsed.name}": {e}')

                    # Normalize to target wavelength range if needed
                    if parsed.spectral:
                        parsed.spectral = self._normalize_spectral(parsed.spectral, warnings)

                    colors.append(parsed)
            except Exception as e:
                errors.append(f'Error parsing color element: {e}')
                logger.exception('Error parsing CXF color element')

        if not colors and errors:
            return CxfParseResult(success=False, errors=errors, warnings=warnings,
                                  file_metadata=file_metadata)

        return CxfParseResult(
            success=True,
            colors=colors,
            errors=errors,
            warnings=warnings,
            file_metadata=file_metadata,
        )

    def _detect_namespace(self, root):
        """Detect the CXF namespace used in the document."""
        nsmap = root.nsmap
        # Check for known CXF namespaces
        for prefix, uri in nsmap.items():
            if 'colorexchangeformat' in uri.lower() or 'cxf' in uri.lower():
                return {'cxf': uri}

        # Check default namespace
        default_ns = nsmap.get(None, '')
        if 'colorexchangeformat' in default_ns.lower() or 'cxf' in default_ns.lower():
            return {'cxf': default_ns}

        # No namespace found — try parsing without
        return {}

    def _extract_file_metadata(self, root, ns):
        """Extract file-level metadata from the CXF document."""
        metadata = {}
        tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        metadata['root_element'] = tag

        # Try to get description/creator
        for path in ['Description', 'Creator', 'CreationDate']:
            elem = self._find(root, path, ns)
            if elem is not None and elem.text:
                metadata[path.lower()] = elem.text.strip()

        return metadata

    def _find_color_elements(self, root, ns):
        """Find all color object elements in the CXF tree."""
        elements = []

        # Try with namespace
        if ns:
            ns_prefix = '{' + ns.get('cxf', '') + '}'
            # Standard CXF/X-4 path: Resources/ObjectCollection/Object
            for path in [
                f'.//{ns_prefix}Object',
                f'.//{ns_prefix}ColorObject',
                f'.//{ns_prefix}ColorSpecification',
            ]:
                found = root.findall(path)
                if found:
                    elements.extend(found)
                    break

        # Try without namespace
        if not elements:
            for path in ['.//Object', './/ColorObject', './/ColorSpecification']:
                found = root.findall(path)
                if found:
                    elements.extend(found)
                    break

        return elements

    def _parse_color_element(self, elem, ns) -> Optional[ParsedColor]:
        """Parse a single color object element."""
        color = ParsedColor()

        # Get color name
        name = elem.get('Name') or elem.get('name') or elem.get('Id') or elem.get('id', '')
        color.name = name

        # Extract spectral data
        spectral = self._extract_spectral(elem, ns)
        if spectral:
            color.spectral = spectral

        # Extract LAB values
        lab = self._extract_lab(elem, ns)
        if lab:
            color.lab_l, color.lab_a, color.lab_b = lab

        # At least one of spectral or LAB must be present
        if not color.spectral and color.lab_l is None:
            return None

        return color

    def _extract_spectral(self, elem, ns) -> Optional[SpectralData]:
        """Extract spectral reflectance data from a color element."""
        # Look for spectral data in various possible locations
        spectral_elem = None
        for tag in ['ReflectanceSpectrum', 'SpectralData', 'Spectrum',
                     'ColorSpectrum', 'ReflectanceData']:
            spectral_elem = self._find_descendant(elem, tag, ns)
            if spectral_elem is not None:
                break

        if spectral_elem is None:
            return None

        # Get wavelength range
        wl_start = self._get_int_attr(spectral_elem, ['StartWL', 'StartWavelength',
                                                        'WavelengthStart', 'startWL'], 360)
        wl_end = self._get_int_attr(spectral_elem, ['EndWL', 'EndWavelength',
                                                      'WavelengthEnd', 'endWL'], 780)
        wl_interval = self._get_int_attr(spectral_elem, ['Interval', 'WavelengthInterval',
                                                           'Step', 'interval'], 10)

        # Parse reflectance values
        text = spectral_elem.text
        if not text or not text.strip():
            # Values might be in child elements
            values = []
            for child in spectral_elem:
                if child.text and child.text.strip():
                    try:
                        values.append(float(child.text.strip()))
                    except ValueError:
                        continue
            if not values:
                return None
        else:
            # Values as whitespace or comma separated text
            text = text.strip().replace(',', ' ').replace(';', ' ')
            try:
                values = [float(v) for v in text.split()]
            except ValueError:
                return None

        if not values:
            return None

        return SpectralData(
            reflectance=values,
            wavelength_start=wl_start,
            wavelength_end=wl_end,
            wavelength_interval=wl_interval,
        )

    def _extract_lab(self, elem, ns) -> Optional[tuple]:
        """Extract CIELAB values from a color element."""
        # Try various element names for LAB data
        for lab_tag in ['ColorCIELab', 'CIELab', 'Lab', 'CIELAB']:
            lab_elem = self._find_descendant(elem, lab_tag, ns)
            if lab_elem is not None:
                l_val = self._get_float_child(lab_elem, ['L', 'CIE-L'], ns)
                a_val = self._get_float_child(lab_elem, ['A', 'CIE-a', 'a'], ns)
                b_val = self._get_float_child(lab_elem, ['B', 'CIE-b', 'b'], ns)
                if l_val is not None and a_val is not None and b_val is not None:
                    return (l_val, a_val, b_val)

                # Try as attributes
                l_val = self._get_float_attr(lab_elem, ['L', 'l'])
                a_val = self._get_float_attr(lab_elem, ['A', 'a'])
                b_val = self._get_float_attr(lab_elem, ['B', 'b'])
                if l_val is not None and a_val is not None and b_val is not None:
                    return (l_val, a_val, b_val)

        return None

    def _normalize_spectral(self, spectral: SpectralData,
                            warnings: list) -> SpectralData:
        """Normalize spectral data to the target wavelength range.

        If the source data has a different range or interval, interpolate to match
        the target 360-780nm at 10nm intervals.
        """
        if (spectral.wavelength_start == self.TARGET_WL_START and
                spectral.wavelength_end == self.TARGET_WL_END and
                spectral.wavelength_interval == self.TARGET_WL_INTERVAL and
                len(spectral.reflectance) == 43):
            return spectral

        import numpy as np

        source_wl = np.array(spectral.wavelengths, dtype=float)
        source_vals = np.array(spectral.reflectance, dtype=float)
        target_wl = np.arange(self.TARGET_WL_START, self.TARGET_WL_END + 1,
                              self.TARGET_WL_INTERVAL, dtype=float)

        # Check if target range is within source range
        if target_wl[0] < source_wl[0] or target_wl[-1] > source_wl[-1]:
            warnings.append(
                f'Source wavelength range ({spectral.wavelength_start}-{spectral.wavelength_end}nm) '
                f'does not fully cover target range ({self.TARGET_WL_START}-{self.TARGET_WL_END}nm). '
                f'Extrapolated values may be less accurate.'
            )

        # Interpolate
        interp_vals = np.interp(target_wl, source_wl, source_vals)
        # Clamp to valid range
        interp_vals = np.clip(interp_vals, 0.0, 2.0)

        return SpectralData(
            reflectance=interp_vals.tolist(),
            wavelength_start=self.TARGET_WL_START,
            wavelength_end=self.TARGET_WL_END,
            wavelength_interval=self.TARGET_WL_INTERVAL,
        )

    # --- XML helper methods ---

    def _find(self, parent, tag, ns):
        """Find a direct child element by tag name, with or without namespace."""
        if ns:
            ns_uri = ns.get('cxf', '')
            result = parent.find(f'{{{ns_uri}}}{tag}')
            if result is not None:
                return result
        return parent.find(tag)

    def _find_descendant(self, parent, tag, ns):
        """Find a descendant element by tag name, with or without namespace."""
        if ns:
            ns_uri = ns.get('cxf', '')
            result = parent.find(f'.//{{{ns_uri}}}{tag}')
            if result is not None:
                return result
        return parent.find(f'.//{tag}')

    def _get_int_attr(self, elem, names, default):
        for name in names:
            val = elem.get(name)
            if val is not None:
                try:
                    return int(val)
                except ValueError:
                    continue
        return default

    def _get_float_attr(self, elem, names):
        for name in names:
            val = elem.get(name)
            if val is not None:
                try:
                    return float(val)
                except ValueError:
                    continue
        return None

    def _get_float_child(self, parent, tags, ns):
        for tag in tags:
            elem = self._find(parent, tag, ns)
            if elem is None:
                elem = self._find_descendant(parent, tag, ns)
            if elem is not None and elem.text:
                try:
                    return float(elem.text.strip())
                except ValueError:
                    continue
        return None
