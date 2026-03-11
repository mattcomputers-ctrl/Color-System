"""Tests for CXF file parser."""

import pytest

from app.services.cxf_parser import CxfParser, SpectralData


@pytest.fixture
def parser():
    return CxfParser()


def _make_cxf(reflectance_values, name='TestColor',
              wl_start=360, wl_end=780, wl_interval=10,
              include_lab=False, namespace=True):
    """Build a minimal CXF/X-4 XML string for testing."""
    values_str = ' '.join(f'{v:.6f}' for v in reflectance_values)

    lab_xml = ''
    if include_lab:
        lab_xml = '''
        <ColorCIELab>
            <L>50.0</L>
            <A>10.0</A>
            <B>-20.0</B>
        </ColorCIELab>'''

    if namespace:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<CxF xmlns="http://colorexchangeformat.com/CxF3-core">
  <Resources>
    <ObjectCollection>
      <Object Name="{name}">
        <ReflectanceSpectrum StartWL="{wl_start}" EndWL="{wl_end}" Interval="{wl_interval}">
          {values_str}
        </ReflectanceSpectrum>
        {lab_xml}
      </Object>
    </ObjectCollection>
  </Resources>
</CxF>'''.encode('utf-8')
    else:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<CxF>
  <Resources>
    <ObjectCollection>
      <Object Name="{name}">
        <ReflectanceSpectrum StartWL="{wl_start}" EndWL="{wl_end}" Interval="{wl_interval}">
          {values_str}
        </ReflectanceSpectrum>
        {lab_xml}
      </Object>
    </ObjectCollection>
  </Resources>
</CxF>'''.encode('utf-8')


class TestCxfParser:
    def test_parse_valid_43_values(self, parser):
        """Parse CXF with standard 43 spectral values (360-780nm, 10nm)."""
        values = [0.05 + i * 0.02 for i in range(43)]
        data = _make_cxf(values)
        result = parser.parse_bytes(data)

        assert result.success
        assert len(result.colors) == 1
        color = result.primary_color
        assert color.name == 'TestColor'
        assert color.spectral is not None
        assert len(color.spectral.reflectance) == 43

    def test_parse_without_namespace(self, parser):
        """Parse CXF without XML namespace."""
        values = [0.5] * 43
        data = _make_cxf(values, namespace=False)
        result = parser.parse_bytes(data)

        assert result.success
        assert result.primary_color.spectral is not None

    def test_parse_with_lab(self, parser):
        """Parse CXF containing LAB values."""
        values = [0.5] * 43
        data = _make_cxf(values, include_lab=True)
        result = parser.parse_bytes(data)

        assert result.success
        color = result.primary_color
        assert color.lab_l == pytest.approx(50.0)
        assert color.lab_a == pytest.approx(10.0)
        assert color.lab_b == pytest.approx(-20.0)

    def test_parse_different_wavelength_range(self, parser):
        """Parse CXF with 380-730nm range — should be interpolated to 360-780nm."""
        values = [0.3 + 0.01 * i for i in range(36)]  # 380-730nm at 10nm = 36 values
        data = _make_cxf(values, wl_start=380, wl_end=730, wl_interval=10)
        result = parser.parse_bytes(data)

        assert result.success
        color = result.primary_color
        # Should be normalized to 43 values (360-780nm)
        assert len(color.spectral.reflectance) == 43
        assert color.spectral.wavelength_start == 360
        assert color.spectral.wavelength_end == 780

    def test_parse_invalid_xml(self, parser):
        """Invalid XML should return error."""
        result = parser.parse_bytes(b'not xml at all')
        assert not result.success
        assert any('XML' in e or 'xml' in e.lower() for e in result.errors)

    def test_parse_empty_cxf(self, parser):
        """CXF with no color objects should return error."""
        data = b'''<?xml version="1.0"?>
        <CxF xmlns="http://colorexchangeformat.com/CxF3-core">
          <Resources><ObjectCollection></ObjectCollection></Resources>
        </CxF>'''
        result = parser.parse_bytes(data)
        assert not result.success

    def test_comma_separated_values(self, parser):
        """Values separated by commas should also parse."""
        values = [0.5] * 43
        values_str = ','.join(f'{v:.4f}' for v in values)
        data = f'''<?xml version="1.0"?>
        <CxF>
          <Object Name="Test">
            <ReflectanceSpectrum StartWL="360" EndWL="780" Interval="10">
              {values_str}
            </ReflectanceSpectrum>
          </Object>
        </CxF>'''.encode('utf-8')
        result = parser.parse_bytes(data)
        assert result.success


class TestSpectralData:
    def test_validate_correct(self):
        """Valid spectral data should pass validation."""
        sd = SpectralData(reflectance=[0.5] * 43)
        errors = sd.validate()
        assert len(errors) == 0

    def test_validate_wrong_count(self):
        """Wrong number of values should fail validation."""
        sd = SpectralData(reflectance=[0.5] * 40)
        errors = sd.validate()
        assert len(errors) > 0
        assert 'Expected 43' in errors[0]

    def test_validate_negative(self):
        """Negative reflectance should be flagged."""
        values = [0.5] * 43
        values[10] = -0.1
        sd = SpectralData(reflectance=values)
        errors = sd.validate()
        assert any('Negative' in e for e in errors)

    def test_wavelengths_property(self):
        """Wavelengths should be generated correctly."""
        sd = SpectralData(reflectance=[], wavelength_start=400, wavelength_end=700,
                          wavelength_interval=20)
        wls = sd.wavelengths
        assert wls[0] == 400
        assert wls[-1] == 700
        assert len(wls) == 16
