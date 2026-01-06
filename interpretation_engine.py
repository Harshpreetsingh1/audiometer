#!/usr/bin/env python3
"""
Interpretation Engine Module

Rule-based diagnostic analysis for audiometry test results.
Provides automated interpretation and suggestions based on clinical guidelines.

Author: Audiometry Application
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)


class InterpretationEngine:
    """
    Smart interpretation engine for audiometry results.
    
    Analyzes hearing thresholds and provides:
    - Hearing loss classification per ear
    - Pattern detection (flat, sloping, notch)
    - Pure Tone Average (PTA) calculation
    - Clinical remarks and recommendations
    
    Based on WHO/ASHA hearing loss classification standards.
    
    Example Usage:
        >>> engine = InterpretationEngine()
        >>> result = engine.analyze(
        ...     left_ear={500: 25, 1000: 30, 2000: 35, 4000: 45},
        ...     right_ear={500: 20, 1000: 25, 2000: 25, 4000: 30}
        ... )
        >>> print(result['remarks'])
    """
    
    # Hearing loss classification thresholds (WHO/ASHA standards)
    CLASSIFICATION_THRESHOLDS = [
        (-10, 25, "Normal Hearing"),
        (26, 40, "Mild Loss"),
        (41, 55, "Moderate Loss"),
        (56, 70, "Moderately Severe Loss"),
        (71, 90, "Severe Loss"),
        (91, 120, "Profound Loss"),
    ]
    
    # Key frequencies for analysis
    SPEECH_FREQUENCIES = [500, 1000, 2000]  # For PTA calculation
    HIGH_FREQUENCIES = [4000, 8000]
    LOW_FREQUENCIES = [250, 500]
    
    # Thresholds for specific conditions
    NIHL_NOTCH_THRESHOLD = 25  # dB above adjacent frequencies for notch detection
    ASYMMETRY_THRESHOLD = 15   # dB difference between ears
    SIGNIFICANT_LOSS_THRESHOLD = 25  # dB HL
    
    def __init__(self):
        """Initialize the interpretation engine."""
        pass
    
    def analyze(
        self,
        left_ear: Dict[int, float],
        right_ear: Dict[int, float],
        patient_age: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of audiometry results.
        
        Args:
            left_ear: Dict of {frequency_hz: threshold_db} for left ear.
            right_ear: Dict of {frequency_hz: threshold_db} for right ear.
            patient_age: Optional patient age for age-related interpretation.
            
        Returns:
            Dict containing analysis results:
            {
                'left_ear': {classification, pta, pattern, ...},
                'right_ear': {classification, pta, pattern, ...},
                'bilateral': {symmetry, overall_assessment},
                'remarks': [list of diagnostic remarks],
                'recommendations': [list of recommendations],
                'summary': str
            }
        """
        # Normalize frequency keys to integers
        left_ear = self._normalize_frequencies(left_ear)
        right_ear = self._normalize_frequencies(right_ear)
        
        # Analyze each ear
        left_analysis = self._analyze_ear(left_ear, "left")
        right_analysis = self._analyze_ear(right_ear, "right")
        
        # Bilateral analysis
        bilateral = self._analyze_bilateral(left_ear, right_ear, left_analysis, right_analysis)
        
        # Generate remarks and recommendations
        remarks = self._generate_remarks(left_analysis, right_analysis, bilateral, patient_age)
        recommendations = self._generate_recommendations(left_analysis, right_analysis, bilateral)
        
        # Summary
        summary = self._generate_summary(left_analysis, right_analysis)
        
        return {
            'left_ear': left_analysis,
            'right_ear': right_analysis,
            'bilateral': bilateral,
            'remarks': remarks,
            'recommendations': recommendations,
            'summary': summary
        }
    
    def _normalize_frequencies(self, ear_data: Dict) -> Dict[int, float]:
        """Convert frequency keys to integers."""
        return {int(k): float(v) for k, v in ear_data.items()}
    
    def _analyze_ear(self, ear_data: Dict[int, float], ear_name: str) -> Dict[str, Any]:
        """
        Analyze a single ear's audiometry data.
        
        Args:
            ear_data: Dict of {frequency: threshold} for the ear.
            ear_name: 'left' or 'right'.
            
        Returns:
            Dict with analysis results for this ear.
        """
        if not ear_data:
            return {
                'classification': 'No Data',
                'pta': None,
                'pattern': 'Unknown',
                'worst_frequency': None,
                'worst_threshold': None,
                'has_loss': False
            }
        
        # Calculate PTA (Pure Tone Average)
        pta = self._calculate_pta(ear_data)
        
        # Classify hearing level
        classification = self._classify_hearing(pta)
        
        # Detect pattern
        pattern = self._detect_pattern(ear_data)
        
        # Find worst threshold
        worst_freq = max(ear_data.keys(), key=lambda f: ear_data[f])
        worst_threshold = ear_data[worst_freq]
        
        # Check if there's significant loss
        has_loss = any(v > self.SIGNIFICANT_LOSS_THRESHOLD for v in ear_data.values())
        
        # Check for specific conditions
        has_notch = self._detect_4k_notch(ear_data)
        high_freq_loss = self._check_high_frequency_loss(ear_data)
        
        return {
            'classification': classification,
            'pta': round(pta, 1) if pta else None,
            'pattern': pattern,
            'worst_frequency': worst_freq,
            'worst_threshold': worst_threshold,
            'has_loss': has_loss,
            'has_4k_notch': has_notch,
            'high_frequency_loss': high_freq_loss,
            'thresholds': ear_data
        }
    
    def _calculate_pta(self, ear_data: Dict[int, float]) -> Optional[float]:
        """
        Calculate Pure Tone Average (PTA) from speech frequencies.
        
        PTA is the average of thresholds at 500, 1000, and 2000 Hz.
        
        Args:
            ear_data: Dict of {frequency: threshold}.
            
        Returns:
            PTA value or None if insufficient data.
        """
        speech_thresholds = []
        for freq in self.SPEECH_FREQUENCIES:
            if freq in ear_data:
                speech_thresholds.append(ear_data[freq])
        
        if len(speech_thresholds) >= 2:
            return sum(speech_thresholds) / len(speech_thresholds)
        
        # Fallback: use all available frequencies
        if ear_data:
            return sum(ear_data.values()) / len(ear_data)
        
        return None
    
    def _classify_hearing(self, pta: Optional[float]) -> str:
        """
        Classify hearing loss severity based on PTA.
        
        Args:
            pta: Pure Tone Average in dB HL.
            
        Returns:
            Classification string (e.g., "Mild Loss").
        """
        if pta is None:
            return "Unknown"
        
        for min_db, max_db, classification in self.CLASSIFICATION_THRESHOLDS:
            if min_db <= pta <= max_db:
                return classification
        
        return "Profound Loss" if pta > 90 else "Normal Hearing"
    
    def _detect_pattern(self, ear_data: Dict[int, float]) -> str:
        """
        Detect the audiogram pattern.
        
        Patterns:
        - Flat: Similar thresholds across frequencies
        - Sloping: Progressive loss at higher frequencies
        - Rising: Progressive loss at lower frequencies
        - Notched: Characteristic 4kHz dip (NIHL)
        - Cookie-bite: Loss in mid-frequencies
        
        Args:
            ear_data: Dict of {frequency: threshold}.
            
        Returns:
            Pattern name.
        """
        if len(ear_data) < 3:
            return "Insufficient Data"
        
        sorted_freqs = sorted(ear_data.keys())
        thresholds = [ear_data[f] for f in sorted_freqs]
        
        # Calculate range of thresholds
        threshold_range = max(thresholds) - min(thresholds)
        
        # Flat: less than 20dB variation
        if threshold_range < 20:
            return "Flat"
        
        # Check for 4kHz notch (NIHL pattern)
        if self._detect_4k_notch(ear_data):
            return "Notched (4kHz)"
        
        # Calculate overall slope
        low_freq_avg = sum(ear_data.get(f, 0) for f in [250, 500] if f in ear_data)
        low_count = sum(1 for f in [250, 500] if f in ear_data)
        
        high_freq_avg = sum(ear_data.get(f, 0) for f in [4000, 8000] if f in ear_data)
        high_count = sum(1 for f in [4000, 8000] if f in ear_data)
        
        if low_count and high_count:
            low_avg = low_freq_avg / low_count
            high_avg = high_freq_avg / high_count
            
            if high_avg > low_avg + 15:
                return "High-Frequency Sloping"
            elif low_avg > high_avg + 15:
                return "Low-Frequency (Rising)"
        
        # Check for cookie-bite (mid-frequency loss)
        if self._detect_cookie_bite(ear_data):
            return "Cookie-Bite (Mid-Frequency)"
        
        return "Irregular"
    
    def _detect_4k_notch(self, ear_data: Dict[int, float]) -> bool:
        """
        Detect the characteristic 4kHz notch indicating NIHL.
        
        A notch exists if the threshold at 4kHz is significantly worse
        than at adjacent frequencies (2kHz and 8kHz).
        
        Args:
            ear_data: Dict of {frequency: threshold}.
            
        Returns:
            True if 4kHz notch is detected.
        """
        if 4000 not in ear_data:
            return False
        
        threshold_4k = ear_data[4000]
        
        # Compare with adjacent frequencies
        comparisons = []
        if 2000 in ear_data:
            comparisons.append(threshold_4k - ear_data[2000])
        if 8000 in ear_data:
            comparisons.append(threshold_4k - ear_data[8000])
        
        # Notch if 4kHz is at least 10dB worse than average of neighbors
        if comparisons:
            avg_difference = sum(comparisons) / len(comparisons)
            return avg_difference >= 10
        
        return False
    
    def _detect_cookie_bite(self, ear_data: Dict[int, float]) -> bool:
        """
        Detect cookie-bite audiogram pattern.
        
        Cookie-bite shows loss primarily in mid-frequencies (1-2kHz)
        with better hearing at low and high frequencies.
        
        Args:
            ear_data: Dict of {frequency: threshold}.
            
        Returns:
            True if cookie-bite pattern is detected.
        """
        mid_freqs = [1000, 2000]
        low_freqs = [250, 500]
        high_freqs = [4000, 8000]
        
        mid_vals = [ear_data[f] for f in mid_freqs if f in ear_data]
        low_vals = [ear_data[f] for f in low_freqs if f in ear_data]
        high_vals = [ear_data[f] for f in high_freqs if f in ear_data]
        
        if mid_vals and low_vals and high_vals:
            mid_avg = sum(mid_vals) / len(mid_vals)
            low_avg = sum(low_vals) / len(low_vals)
            high_avg = sum(high_vals) / len(high_vals)
            
            # Cookie-bite if mid is worse than both low and high
            return mid_avg > low_avg + 10 and mid_avg > high_avg + 10
        
        return False
    
    def _check_high_frequency_loss(self, ear_data: Dict[int, float]) -> bool:
        """Check for significant high-frequency hearing loss."""
        high_freq_thresholds = [ear_data.get(f, 0) for f in [4000, 8000] if f in ear_data]
        if high_freq_thresholds:
            return max(high_freq_thresholds) > self.SIGNIFICANT_LOSS_THRESHOLD
        return False
    
    def _analyze_bilateral(
        self,
        left_ear: Dict[int, float],
        right_ear: Dict[int, float],
        left_analysis: Dict[str, Any],
        right_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze bilateral hearing characteristics.
        
        Checks for asymmetry between ears and provides overall assessment.
        """
        # Check symmetry at each frequency
        asymmetric_frequencies = []
        max_asymmetry = 0
        
        common_freqs = set(left_ear.keys()) & set(right_ear.keys())
        for freq in common_freqs:
            diff = abs(left_ear[freq] - right_ear[freq])
            if diff > self.ASYMMETRY_THRESHOLD:
                asymmetric_frequencies.append(freq)
            max_asymmetry = max(max_asymmetry, diff)
        
        is_asymmetric = len(asymmetric_frequencies) > 0
        
        # Determine which ear is worse
        left_pta = left_analysis.get('pta') or 0
        right_pta = right_analysis.get('pta') or 0
        worse_ear = 'left' if left_pta > right_pta else 'right' if right_pta > left_pta else 'equal'
        
        # Overall assessment
        left_class = left_analysis.get('classification', 'Unknown')
        right_class = right_analysis.get('classification', 'Unknown')
        
        if left_class == right_class:
            overall = f"Bilateral {left_class}"
        else:
            overall = f"Asymmetric: Left ({left_class}), Right ({right_class})"
        
        return {
            'is_symmetric': not is_asymmetric,
            'asymmetric_frequencies': asymmetric_frequencies,
            'max_asymmetry_db': max_asymmetry,
            'worse_ear': worse_ear,
            'overall_assessment': overall
        }
    
    def _generate_remarks(
        self,
        left_analysis: Dict[str, Any],
        right_analysis: Dict[str, Any],
        bilateral: Dict[str, Any],
        patient_age: Optional[int]
    ) -> List[str]:
        """
        Generate clinical remarks based on analysis.
        
        Returns:
            List of diagnostic remarks.
        """
        remarks = []
        
        # Check for NIHL (Noise-Induced Hearing Loss)
        if left_analysis.get('has_4k_notch') or right_analysis.get('has_4k_notch'):
            affected_ears = []
            if left_analysis.get('has_4k_notch'):
                affected_ears.append("left")
            if right_analysis.get('has_4k_notch'):
                affected_ears.append("right")
            
            ear_text = " and ".join(affected_ears) + " ear" + ("s" if len(affected_ears) > 1 else "")
            remarks.append(f"Signs of Noise-Induced Hearing Loss detected in {ear_text} (4kHz notch pattern)")
        
        # Check for high-frequency loss with age consideration
        if left_analysis.get('high_frequency_loss') or right_analysis.get('high_frequency_loss'):
            if patient_age and patient_age >= 50:
                remarks.append("High-frequency hearing loss consistent with age-related changes (presbycusis)")
            else:
                remarks.append("High-frequency hearing loss detected - recommend noise exposure evaluation")
        
        # Check for asymmetry
        if not bilateral.get('is_symmetric'):
            max_diff = bilateral.get('max_asymmetry_db', 0)
            remarks.append(f"Significant asymmetry detected (up to {max_diff:.0f} dB difference) - recommend medical evaluation")
        
        # Pattern-specific remarks
        for ear_name, analysis in [('Left', left_analysis), ('Right', right_analysis)]:
            pattern = analysis.get('pattern', '')
            if pattern == 'Flat' and analysis.get('has_loss'):
                remarks.append(f"{ear_name} ear shows flat hearing loss - consider conductive hearing loss evaluation")
            elif pattern == 'Cookie-Bite (Mid-Frequency)':
                remarks.append(f"{ear_name} ear shows mid-frequency loss pattern - may indicate genetic factors")
        
        # Overall hearing status
        if left_analysis.get('classification') == 'Normal Hearing' and right_analysis.get('classification') == 'Normal Hearing':
            remarks.append("Hearing within normal limits bilaterally")
        
        return remarks
    
    def _generate_recommendations(
        self,
        left_analysis: Dict[str, Any],
        right_analysis: Dict[str, Any],
        bilateral: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations based on analysis.
        
        Returns:
            List of recommended actions.
        """
        recommendations = []
        
        # Get worst classification
        left_class = left_analysis.get('classification', 'Normal Hearing')
        right_class = right_analysis.get('classification', 'Normal Hearing')
        
        has_significant_loss = any(c not in ['Normal Hearing', 'Unknown', 'No Data'] 
                                   for c in [left_class, right_class])
        
        if has_significant_loss:
            # Recommend based on severity
            for classification in [left_class, right_class]:
                if 'Severe' in classification or 'Profound' in classification:
                    recommendations.append("Urgent referral to ENT specialist recommended")
                    recommendations.append("Consider hearing aid evaluation")
                    break
                elif 'Moderate' in classification:
                    recommendations.append("Referral to audiologist for hearing aid evaluation")
                    break
                elif 'Mild' in classification:
                    recommendations.append("Follow-up audiometry in 6-12 months")
        
        # Asymmetry recommendations
        if not bilateral.get('is_symmetric'):
            recommendations.append("Medical evaluation recommended due to asymmetric hearing loss")
        
        # NIHL recommendations
        if left_analysis.get('has_4k_notch') or right_analysis.get('has_4k_notch'):
            recommendations.append("Recommend hearing protection in noisy environments")
            recommendations.append("Annual audiometry monitoring advised")
        
        # Normal hearing
        if not has_significant_loss:
            recommendations.append("Routine hearing check recommended in 2-3 years")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _generate_summary(
        self,
        left_analysis: Dict[str, Any],
        right_analysis: Dict[str, Any]
    ) -> str:
        """Generate a one-line summary of the findings."""
        left_class = left_analysis.get('classification', 'Unknown')
        right_class = right_analysis.get('classification', 'Unknown')
        
        left_pta = left_analysis.get('pta')
        right_pta = right_analysis.get('pta')
        
        if left_class == right_class:
            if left_class == 'Normal Hearing':
                return "Hearing within normal limits bilaterally."
            else:
                return f"Bilateral {left_class.lower()}."
        else:
            summary_parts = []
            if left_class != 'Normal Hearing':
                summary_parts.append(f"Left ear: {left_class.lower()}")
            if right_class != 'Normal Hearing':
                summary_parts.append(f"Right ear: {right_class.lower()}")
            return "; ".join(summary_parts) + "." if summary_parts else "Hearing assessment complete."
    
    def get_quick_interpretation(
        self,
        left_ear: Dict[int, float],
        right_ear: Dict[int, float]
    ) -> str:
        """
        Get a quick one-line interpretation (for UI display).
        
        Args:
            left_ear: Dict of {frequency: threshold} for left ear.
            right_ear: Dict of {frequency: threshold} for right ear.
            
        Returns:
            One-line interpretation string.
        """
        result = self.analyze(left_ear, right_ear)
        return result['summary']


# Module test
if __name__ == '__main__':
    engine = InterpretationEngine()
    
    # Test case 1: Normal hearing
    print("=" * 60)
    print("Test 1: Normal Hearing")
    result = engine.analyze(
        left_ear={500: 15, 1000: 10, 2000: 15, 4000: 20},
        right_ear={500: 10, 1000: 15, 2000: 10, 4000: 15}
    )
    print(f"Summary: {result['summary']}")
    print(f"Remarks: {result['remarks']}")
    print()
    
    # Test case 2: NIHL pattern
    print("=" * 60)
    print("Test 2: Noise-Induced Hearing Loss Pattern")
    result = engine.analyze(
        left_ear={500: 15, 1000: 15, 2000: 20, 4000: 45, 8000: 30},
        right_ear={500: 10, 1000: 15, 2000: 15, 4000: 40, 8000: 25}
    )
    print(f"Summary: {result['summary']}")
    print(f"Left ear pattern: {result['left_ear']['pattern']}")
    print(f"Has 4k notch: {result['left_ear']['has_4k_notch']}")
    print(f"Remarks: {result['remarks']}")
    print()
    
    # Test case 3: Asymmetric loss
    print("=" * 60)
    print("Test 3: Asymmetric Hearing Loss")
    result = engine.analyze(
        left_ear={500: 45, 1000: 50, 2000: 55, 4000: 60},
        right_ear={500: 15, 1000: 15, 2000: 20, 4000: 25}
    )
    print(f"Summary: {result['summary']}")
    print(f"Bilateral assessment: {result['bilateral']['overall_assessment']}")
    print(f"Is symmetric: {result['bilateral']['is_symmetric']}")
    print(f"Remarks: {result['remarks']}")
    print(f"Recommendations: {result['recommendations']}")
    print()
    
    # Test case 4: Quick interpretation
    print("=" * 60)
    print("Test 4: Quick Interpretation")
    quick = engine.get_quick_interpretation(
        left_ear={500: 30, 1000: 35, 2000: 40, 4000: 45},
        right_ear={500: 25, 1000: 30, 2000: 35, 4000: 40}
    )
    print(f"Quick interpretation: {quick}")
