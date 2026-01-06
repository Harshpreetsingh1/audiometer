#!/usr/bin/env python3
"""
Audiogram Visualizer Module

A robust Python module for reading patient CSV files and generating 
clinical-standard Audiogram plots following ANSI/ISO 8253-1 standards.

Author: Audiometry Application
"""

# CRITICAL: Set matplotlib backend BEFORE importing pyplot
# This prevents GUI crashes when called from background threads
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for thread safety

import csv
import io
import base64
import os
from typing import Optional, Tuple, Dict, List, Any

import matplotlib.pyplot as plt
import numpy as np

# Try to import pandas, fall back to manual CSV handling if not available
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class AudiogramPlotter:
    """
    Clinical-standard audiogram plotter from CSV data.
    
    Generates audiogram plots following clinical standards:
    - Logarithmic X-axis with fixed frequency ticks
    - Inverted Y-axis (0 at top, 120 at bottom)
    - Left ear: Blue 'X' markers with solid line
    - Right ear: Red 'O' markers with solid line
    
    Example Usage:
        >>> plotter = AudiogramPlotter("path/to/patient_test.csv")
        >>> plotter.plot_audiogram("output_graph.png")
        
        # Or get base64 for HTML embedding:
        >>> base64_str = plotter.get_base64_image()
    """
    
    # Clinical standard colors
    LEFT_EAR_COLOR = '#0000FF'   # Blue
    RIGHT_EAR_COLOR = '#FF0000'  # Red
    
    # Clinical standard markers
    LEFT_EAR_MARKER = 'x'   # X marker for left ear
    RIGHT_EAR_MARKER = 'o'  # Circle marker for right ear
    
    # Standard audiometric frequencies (Hz)
    STANDARD_FREQUENCIES = [125, 250, 500, 1000, 2000, 4000, 8000]
    
    # Y-axis range (dB HL)
    Y_MIN = -10
    Y_MAX = 120
    Y_STEP = 10
    
    def __init__(self, file_path: str):
        """
        Initialize the AudiogramPlotter with a CSV file.
        
        Args:
            file_path: Path to the patient test CSV file.
            
        Raises:
            FileNotFoundError: If the CSV file doesn't exist.
            ValueError: If the CSV format is invalid.
        """
        self.file_path = file_path
        self.metadata: Dict[str, str] = {}
        self.data: List[Dict[str, Any]] = []
        self._figure: Optional[plt.Figure] = None
        
        # Parse the CSV file on initialization
        self.metadata, self.data = self.parse_csv(file_path)
    
    def parse_csv(self, file_path: str) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
        """
        Read and parse the CSV file, separating metadata from audiogram data.
        
        The CSV format has variable metadata rows at the top, followed by a 
        header row starting with 'Level/dB', then the actual test data.
        
        Example CSV format:
            Conduction,air,
            Masking,off,
            Level/dB,Frequency/Hz,Earside
            20,1000,Left
            25,2000,Left
        
        Args:
            file_path: Path to the CSV file.
            
        Returns:
            Tuple of (metadata_dict, data_list):
                - metadata_dict: Dict with keys like 'Conduction', 'Masking'
                - data_list: List of dicts with 'Level/dB', 'Frequency/Hz', 'Earside'
                
        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If header row 'Level/dB' is not found.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")
        
        metadata: Dict[str, str] = {}
        data: List[Dict[str, Any]] = []
        header_found = False
        header_columns: List[str] = []
        
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            
            for row in reader:
                if not row or all(cell.strip() == '' for cell in row):
                    continue  # Skip empty rows
                
                # Check if this is the header row
                if not header_found:
                    first_cell = row[0].strip() if row else ''
                    
                    if first_cell == 'Level/dB':
                        # Found the header row
                        header_found = True
                        header_columns = [col.strip() for col in row]
                    else:
                        # This is a metadata row
                        if len(row) >= 2:
                            key = row[0].strip()
                            value = row[1].strip()
                            if key:
                                metadata[key] = value
                else:
                    # This is a data row
                    if len(row) >= 3:
                        try:
                            level = float(row[0].strip())
                            freq = float(row[1].strip())
                            earside = row[2].strip().lower()
                            
                            data.append({
                                'Level/dB': level,
                                'Frequency/Hz': freq,
                                'Earside': earside
                            })
                        except (ValueError, IndexError):
                            # Skip invalid data rows
                            continue
        
        if not header_found:
            raise ValueError(
                f"Invalid CSV format: Header row starting with 'Level/dB' not found in {file_path}"
            )
        
        return metadata, data
    
    def plot_audiogram(self, save_path: Optional[str] = None) -> plt.Figure:
        """
        Generate a clinical-standard audiogram plot.
        
        Visualization follows clinical standards:
        - X-Axis: Logarithmic scale with fixed ticks [125, 250, 500, 1000, 2000, 4000, 8000]
        - Y-Axis: Inverted linear scale, -10 dB to 120 dB, 10 dB steps
        - Left Ear: Blue (#0000FF), 'X' marker, solid line
        - Right Ear: Red (#FF0000), 'O' (circle) marker, solid line
        - Light grey grid for readability
        
        Args:
            save_path: Optional path to save high-resolution PNG. 
                      If None, returns the figure object without saving.
                      
        Returns:
            matplotlib.figure.Figure: The generated figure object.
        """
        # Create figure with clinical aspect ratio
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Configure the plot title
        fig.suptitle('Pure Tone Audiogram', fontsize=16, fontweight='bold', color='#00838F')
        
        # Separate data by ear
        left_ear_data = [(d['Frequency/Hz'], d['Level/dB']) 
                         for d in self.data if d['Earside'] == 'left']
        right_ear_data = [(d['Frequency/Hz'], d['Level/dB']) 
                          for d in self.data if d['Earside'] == 'right']
        
        # Sort by frequency
        left_ear_data.sort(key=lambda x: x[0])
        right_ear_data.sort(key=lambda x: x[0])
        
        # Plot Right Ear (Red circles)
        if right_ear_data:
            freqs_r, levels_r = zip(*right_ear_data)
            ax.plot(freqs_r, levels_r, 
                   color=self.RIGHT_EAR_COLOR, 
                   marker=self.RIGHT_EAR_MARKER,
                   markersize=10,
                   markeredgewidth=2,
                   markerfacecolor='none',  # Hollow circle
                   linestyle='-',
                   linewidth=1.5,
                   label='Right Ear')
        
        # Plot Left Ear (Blue X markers)
        if left_ear_data:
            freqs_l, levels_l = zip(*left_ear_data)
            ax.plot(freqs_l, levels_l, 
                   color=self.LEFT_EAR_COLOR, 
                   marker=self.LEFT_EAR_MARKER,
                   markersize=10,
                   markeredgewidth=2,
                   linestyle='-',
                   linewidth=1.5,
                   label='Left Ear')
        
        # Configure X-axis (Logarithmic, frequency)
        ax.set_xscale('log')
        ax.set_xlim(100, 10000)  # Slightly beyond the standard range for padding
        ax.set_xticks(self.STANDARD_FREQUENCIES)
        ax.set_xticklabels([str(f) for f in self.STANDARD_FREQUENCIES])
        ax.set_xlabel('Frequency (Hz)', fontsize=12, fontweight='bold', color='#00838F')
        
        # Configure Y-axis (Inverted, hearing level)
        ax.set_ylim(self.Y_MAX, self.Y_MIN)  # Inverted: 120 at bottom, -10 at top
        ax.set_yticks(range(self.Y_MIN, self.Y_MAX + 1, self.Y_STEP))
        ax.set_ylabel('Hearing Level (dB HL)', fontsize=12, fontweight='bold')
        
        # Add secondary x-axis label at top (optional clinical format)
        ax2 = ax.twiny()
        ax2.set_xscale('log')
        ax2.set_xlim(ax.get_xlim())
        ax2.set_xticks(self.STANDARD_FREQUENCIES)
        ax2.set_xticklabels([str(f) for f in self.STANDARD_FREQUENCIES])
        ax2.set_xlabel('Frequency (Hz)', fontsize=10, color='#00838F')
        
        # Add grid
        ax.grid(True, which='major', linestyle='-', linewidth=0.5, color='lightgrey', alpha=0.7)
        ax.grid(True, which='minor', linestyle=':', linewidth=0.3, color='lightgrey', alpha=0.5)
        ax.minorticks_on()
        
        # Add hearing level classification zones (right side annotations)
        self._add_hearing_level_zones(ax)
        
        # Add legend
        legend = ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
        legend.get_frame().set_edgecolor('lightgrey')
        
        # Clinical aspect ratio: try to maintain 1 octave = 20 dB
        # For log scale, this is complex, so we use a square-ish ratio
        ax.set_aspect('auto')
        
        # Tight layout
        plt.tight_layout()
        fig.subplots_adjust(top=0.88)  # Make room for title
        
        # Store figure reference
        self._figure = fig
        
        # Save if path provided
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight', 
                       format='png', facecolor='white', edgecolor='none')
            print(f"Audiogram saved to: {save_path}")
        
        return fig
    
    def _add_hearing_level_zones(self, ax: plt.Axes) -> None:
        """
        Add hearing level classification zones to the right side of the plot.
        
        Classifications based on WHO/ASHA standards:
        - Normal Hearing: -10 to 25 dB
        - Mild Loss: 26 to 40 dB
        - Moderate Loss: 41 to 55 dB
        - Moderately Severe: 56 to 70 dB
        - Severe Loss: 71 to 90 dB
        - Profound Loss: 91+ dB
        """
        # Get the right edge of the plot for text placement
        x_pos = 1.02  # Slightly outside the plot area
        
        classifications = [
            (-10, 25, 'Normal\nHearing'),
            (26, 40, 'Mild'),
            (41, 55, 'Moderate'),
            (56, 70, 'Moderately\nSevere'),
            (71, 90, 'Severe'),
            (91, 120, 'Profound'),
        ]
        
        for y_start, y_end, label in classifications:
            y_center = (y_start + y_end) / 2
            ax.text(x_pos, y_center, label, 
                   transform=ax.get_yaxis_transform(),
                   fontsize=8, 
                   verticalalignment='center',
                   horizontalalignment='left',
                   color='#666666',
                   style='italic')
    
    def get_base64_image(self, dpi: int = 150) -> str:
        """
        Generate the audiogram and return as a base64-encoded PNG string.
        
        This method is useful for embedding the image directly in HTML:
            <img src="data:image/png;base64,{base64_string}">
        
        Args:
            dpi: Resolution of the output image (default: 150).
            
        Returns:
            str: Base64-encoded PNG image string.
        """
        # Generate the plot if not already done
        if self._figure is None:
            self.plot_audiogram()
        
        # Save to BytesIO buffer
        buffer = io.BytesIO()
        self._figure.savefig(buffer, format='png', dpi=dpi, 
                            bbox_inches='tight', facecolor='white', edgecolor='none')
        buffer.seek(0)
        
        # Encode to base64
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        buffer.close()
        
        return image_base64
    
    def get_data_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the parsed audiogram data.
        
        Returns:
            Dict containing metadata and data statistics.
        """
        left_count = sum(1 for d in self.data if d['Earside'] == 'left')
        right_count = sum(1 for d in self.data if d['Earside'] == 'right')
        
        return {
            'metadata': self.metadata,
            'total_measurements': len(self.data),
            'left_ear_measurements': left_count,
            'right_ear_measurements': right_count,
            'frequencies_tested': sorted(set(d['Frequency/Hz'] for d in self.data))
        }
    
    def close(self) -> None:
        """Close the figure and release resources."""
        if self._figure is not None:
            plt.close(self._figure)
            self._figure = None


# Example usage and module test
if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python audiogram_visualizer.py <csv_file> [output_png]")
        print("\nExample:")
        print("  python audiogram_visualizer.py patient_test.csv output.png")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        plotter = AudiogramPlotter(csv_file)
        print(f"Parsed CSV: {plotter.get_data_summary()}")
        
        if output_file:
            plotter.plot_audiogram(output_file)
        else:
            fig = plotter.plot_audiogram()
            print("Figure generated. Use get_base64_image() for HTML embedding.")
            
        plotter.close()
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
