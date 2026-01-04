"""Audiogram."""

# CRITICAL: Set matplotlib backend BEFORE importing pyplot
# This prevents GUI crashes when called from background threads
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for thread safety

import numpy as np
import csv
import matplotlib.pyplot as plt
import os


def set_audiogram_parameters(dBHL, freqs, conduction, masking, earside,
                             ax=None, **kwargs):
    """Set measuring points.

    Parameters
    ----------
    dBHL : array_like
          dB(HearingLevel)
    freqs : array_like
          Frequency Vector in Hz
    ax: plt.Ax, optional
          Matplotlib Ax to plot on
    earside: str, default='left'
          'left' or 'right' ear
    masking: bool, default=False
          Masked or unmasked hearing test
    conduction: str, default='air'
          Air conduction is 'air' and bone conduction is 'bone'
    Returns
    -------
    plt.Axis
        Matplotlib axis containing the plot.

    """
    if ax is None:
        ax = plt.gca()
    xticks = np.arange(len(freqs))
    ax.set_xlabel("f / Hz")
    ax.set_ylabel('Sound Intensity / dBHL')
    ax.set_xlim([-0.5, xticks[-1] + 0.5])
    ax.set_ylim([-20, 120])
    plt.setp(ax, xticks=xticks, xticklabels=sorted(freqs))
    major_ticks = np.arange(-20, 120, 10)
    minor_ticks = np.arange(-20, 120, 5)
    ax.set_yticks(major_ticks)
    ax.set_yticks(minor_ticks, minor=True)
    ax.grid(which='both')
    ax.invert_yaxis()
    
    # Task 5: Add "Normal Hearing Ability" shaded region (-10dB to 25dB)
    # This appears as a light blue/green band at the top of the chart
    # Draw it first with low zorder so data lines appear on top
    ax.axhspan(-10, 25, alpha=0.15, color='#4CAF50', zorder=0,
               label='Normal Hearing (-10 to 25 dB)')
    ax.tick_params(axis='x', labelsize=6.5)
    ax.tick_params(axis='y', labelsize=6.5)
    #  one octave on the frequency axis shall correspond
    #  to 20 dB on the hearing level axis (ISO 8253-1 (2011) ch. 10)
    ax.set_aspect(0.9 / ax.get_data_ratio())
    ax.set_title('Hearing Level - {} ear'.format(earside))
    
    # CLINICAL STANDARD: Right Ear = Red (O), Left Ear = Blue (X)
    # Following ANSI/ISO 8253-1 audiometric standards
    if earside == 'left':
        color = 'b'  # Blue for left ear (clinical standard)
        if conduction == 'air' and masking == 'off':
            marker = 'x'  # X marker for left ear air conduction (clinical standard)
        elif conduction == 'air' and masking == 'on':
            marker = 's'  # Square for left ear air conduction with masking
        elif conduction == 'bone' and masking == 'off':
            marker = '4'  # Triangle down for left ear bone conduction
        elif conduction == 'bone' and masking == 'on':
            marker = '*'  # Star for left ear bone conduction with masking
        else:
            raise NameError("Conduction has to be 'air' or 'bone'")
    elif earside == 'right':
        color = 'r'  # Red for right ear (clinical standard)
        if conduction == 'air' and masking == 'off':
            marker = 'o'  # Circle (O) marker for right ear air conduction (clinical standard)
        elif conduction == 'air' and masking == 'on':
            marker = '^'  # Triangle up for right ear air conduction with masking
        elif conduction == 'bone' and masking == 'off':
            marker = '3'  # Triangle left for right ear bone conduction
        elif conduction == 'bone' and masking == 'on':
            marker = '8'  # Octagon for right ear bone conduction with masking
        else:
            raise NameError("Conduction has to be 'air' or 'bone'")
    elif not earside == 'right' or not earside == 'left':
        raise NameError("'left' or 'right'?")
    # Plot with connecting line (solid for air conduction, dashed for bone)
    # Ensure clinical standard styling: Right=Red(O), Left=Blue(X), inverted Y-axis
    linestyle = '-' if conduction == 'air' else '--'
    lines = ax.plot(dBHL, color=color, marker=marker, markersize=8,
                    markeredgewidth=2.5, markeredgecolor=color,
                    linestyle=linestyle, linewidth=2, fillstyle='none',
                    label='{} ear'.format(earside.capitalize()))
    ax.legend(loc='best')
    gridlines = ax.get_xgridlines() + ax.get_ygridlines()
    for line in gridlines:
        line.set_linestyle('-')
    return lines


def make_audiogram(filename, results_path=None):

        if results_path is None:
            results_path = 'audiometer/results'
        # Ensure results_path ends with separator for proper path joining
        if not results_path.endswith(os.sep) and not results_path.endswith('/'):
            results_path = results_path + os.sep
        
        data = _read_audiogram(filename, results_path)
        conduction = [option for cond, option, none in data
                      if cond == 'Conduction'][0]
        masking = [option for mask, option, none in data
                   if mask == 'Masking'][0]

        if 'right' in [side for freq, level, side in data] and (
           'left' in [side for freq, level, side in data]):
            f, (ax1, ax2) = plt.subplots(ncols=2, figsize=(14, 6))
            f.suptitle('Audiogram - Hearing Threshold Levels', fontsize=14, fontweight='bold')
        else:
            ax1, ax2 = None, None
            f = plt.figure(figsize=(7, 6))
            f.suptitle('Audiogram - Hearing Threshold Levels', fontsize=14, fontweight='bold')

        if 'right' in [side for freq, level, side in data]:
            dBHL, freqs = _extract_parameters(data, 'right')
            set_audiogram_parameters(dBHL, freqs, conduction, masking,
                                     earside='right', ax=ax1)

        if 'left' in [side for freq, level, side in data]:
            dBHL, freqs = _extract_parameters(data, 'left')
            set_audiogram_parameters(dBHL, freqs, conduction, masking,
                                     earside='left', ax=ax2)

        # Save PDF with proper path handling
        # Remove .csv extension if present, then add .pdf
        base_filename = os.path.splitext(filename)[0]
        pdf_path = os.path.join(results_path, base_filename + '.pdf')
        f.savefig(pdf_path, dpi=300, bbox_inches='tight')
        print(f"Audiogram saved to: {pdf_path}")
        
        # Task 5: Also save PNG for web display
        png_path = os.path.join(results_path, base_filename + '.png')
        f.savefig(png_path, dpi=150, bbox_inches='tight', format='png')
        print(f"Audiogram PNG saved to: {png_path}")
        
        plt.close(f)  # Clean up figure to prevent memory leaks


def _read_audiogram(filename, results_path=None):
    """Read audiogram data from CSV file.
    
    Args:
        filename: CSV filename (e.g., 'result_2025-12-15_22-08-12.csv')
        results_path: Path to results directory (supports user folders)
    
    Returns:
        List of CSV rows
    """
    if results_path is None:
        results_path = 'audiometer/results'
    
    # Ensure proper path joining
    if not results_path.endswith(os.sep) and not results_path.endswith('/'):
        results_path = results_path + os.sep
    
    csv_path = os.path.join(results_path, filename)
    with open(csv_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        data = [data for data in reader]
    return data


def _extract_parameters(data, earside):
    parameters = sorted((float(freq), float(level)) for level, freq, side
                        in data if side == earside)
    dBHL = [level for freq, level in parameters]
    freqs = [int(freq) for freq, level in parameters]
    return dBHL, freqs
