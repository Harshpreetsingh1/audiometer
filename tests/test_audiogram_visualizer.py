#!/usr/bin/env python3
"""
Tests for the AudiogramPlotter class in audiogram_visualizer.py

Tests cover:
- CSV parsing with variable metadata rows
- Metadata extraction
- Data parsing
- Plot generation
- Base64 encoding
"""

import os
import sys
import tempfile
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audiogram_visualizer import AudiogramPlotter


class TestAudiogramParsing:
    """Tests for CSV parsing functionality."""
    
    @pytest.fixture
    def sample_csv_file(self, tmp_path):
        """Create a sample CSV file matching the expected format."""
        csv_content = """Conduction,air,
Masking,off,
Level/dB,Frequency/Hz,Earside
20,1000,Left
25,2000,Left
30,4000,Left
15,1000,Right
20,2000,Right
25,4000,Right
"""
        csv_file = tmp_path / "test_audiogram.csv"
        csv_file.write_text(csv_content)
        return str(csv_file)
    
    @pytest.fixture
    def minimal_csv_file(self, tmp_path):
        """Create a CSV with minimal metadata."""
        csv_content = """Level/dB,Frequency/Hz,Earside
20,1000,Left
"""
        csv_file = tmp_path / "minimal.csv"
        csv_file.write_text(csv_content)
        return str(csv_file)
    
    @pytest.fixture
    def extra_metadata_csv_file(self, tmp_path):
        """Create a CSV with extra metadata rows."""
        csv_content = """Conduction,air,
Masking,off,
PatientID,12345,
TestDate,2026-01-06,
ExtraField,value,
Level/dB,Frequency/Hz,Earside
20,1000,Left
25,2000,Right
"""
        csv_file = tmp_path / "extra_metadata.csv"
        csv_file.write_text(csv_content)
        return str(csv_file)
    
    def test_parse_csv_standard_format(self, sample_csv_file):
        """Test parsing a standard CSV file."""
        plotter = AudiogramPlotter(sample_csv_file)
        
        # Check metadata
        assert plotter.metadata.get('Conduction') == 'air'
        assert plotter.metadata.get('Masking') == 'off'
        
        # Check data count
        assert len(plotter.data) == 6
        
        # Check left ear data
        left_data = [d for d in plotter.data if d['Earside'] == 'left']
        assert len(left_data) == 3
        
        # Check right ear data
        right_data = [d for d in plotter.data if d['Earside'] == 'right']
        assert len(right_data) == 3
    
    def test_parse_csv_minimal(self, minimal_csv_file):
        """Test parsing CSV with no metadata (only header + data)."""
        plotter = AudiogramPlotter(minimal_csv_file)
        
        # Should have no metadata
        assert len(plotter.metadata) == 0
        
        # Should have one data row
        assert len(plotter.data) == 1
        assert plotter.data[0]['Level/dB'] == 20
        assert plotter.data[0]['Frequency/Hz'] == 1000
        assert plotter.data[0]['Earside'] == 'left'
    
    def test_parse_csv_extra_metadata(self, extra_metadata_csv_file):
        """Test parsing CSV with extra metadata rows."""
        plotter = AudiogramPlotter(extra_metadata_csv_file)
        
        # Should have all metadata
        assert plotter.metadata.get('Conduction') == 'air'
        assert plotter.metadata.get('Masking') == 'off'
        assert plotter.metadata.get('PatientID') == '12345'
        assert plotter.metadata.get('TestDate') == '2026-01-06'
        assert plotter.metadata.get('ExtraField') == 'value'
        
        # Should have two data rows
        assert len(plotter.data) == 2
    
    def test_parse_csv_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        with pytest.raises(FileNotFoundError):
            AudiogramPlotter("nonexistent_file.csv")
    
    def test_parse_csv_invalid_format(self, tmp_path):
        """Test that ValueError is raised for invalid CSV format."""
        csv_content = """Some,Random,Data
1,2,3
"""
        csv_file = tmp_path / "invalid.csv"
        csv_file.write_text(csv_content)
        
        with pytest.raises(ValueError) as excinfo:
            AudiogramPlotter(str(csv_file))
        
        assert "Header row starting with 'Level/dB' not found" in str(excinfo.value)


class TestAudiogramPlotting:
    """Tests for plot generation functionality."""
    
    @pytest.fixture
    def sample_plotter(self, tmp_path):
        """Create a plotter with sample data."""
        csv_content = """Conduction,air,
Masking,off,
Level/dB,Frequency/Hz,Earside
20,250,Left
25,500,Left
30,1000,Left
35,2000,Left
40,4000,Left
15,250,Right
20,500,Right
25,1000,Right
30,2000,Right
35,4000,Right
"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)
        return AudiogramPlotter(str(csv_file))
    
    def test_plot_returns_figure(self, sample_plotter):
        """Test that plot_audiogram returns a matplotlib figure."""
        import matplotlib.pyplot as plt
        
        fig = sample_plotter.plot_audiogram()
        
        assert fig is not None
        assert isinstance(fig, plt.Figure)
        
        sample_plotter.close()
    
    def test_plot_saves_png(self, sample_plotter, tmp_path):
        """Test that plot_audiogram saves a PNG file."""
        output_path = str(tmp_path / "output.png")
        
        sample_plotter.plot_audiogram(output_path)
        
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0
        
        sample_plotter.close()
    
    def test_get_base64_image(self, sample_plotter):
        """Test that get_base64_image returns valid base64 string."""
        import base64
        
        b64_str = sample_plotter.get_base64_image()
        
        assert b64_str is not None
        assert len(b64_str) > 0
        
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(b64_str)
            # PNG files start with these magic bytes
            assert decoded[:8] == b'\x89PNG\r\n\x1a\n'
        except Exception as e:
            pytest.fail(f"Invalid base64 encoding: {e}")
        
        sample_plotter.close()
    
    def test_get_data_summary(self, sample_plotter):
        """Test the get_data_summary method."""
        summary = sample_plotter.get_data_summary()
        
        assert summary['total_measurements'] == 10
        assert summary['left_ear_measurements'] == 5
        assert summary['right_ear_measurements'] == 5
        assert 'metadata' in summary
        assert 'frequencies_tested' in summary
        
        sample_plotter.close()


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_single_ear_data(self, tmp_path):
        """Test plotting with only one ear's data."""
        csv_content = """Conduction,air,
Masking,off,
Level/dB,Frequency/Hz,Earside
20,1000,Left
25,2000,Left
"""
        csv_file = tmp_path / "single_ear.csv"
        csv_file.write_text(csv_content)
        
        plotter = AudiogramPlotter(str(csv_file))
        fig = plotter.plot_audiogram()
        
        assert fig is not None
        
        plotter.close()
    
    def test_empty_data_rows(self, tmp_path):
        """Test handling of empty rows in CSV."""
        csv_content = """Conduction,air,

Masking,off,

Level/dB,Frequency/Hz,Earside

20,1000,Left

25,2000,Right
"""
        csv_file = tmp_path / "empty_rows.csv"
        csv_file.write_text(csv_content)
        
        plotter = AudiogramPlotter(str(csv_file))
        
        assert len(plotter.data) == 2
        
        plotter.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
