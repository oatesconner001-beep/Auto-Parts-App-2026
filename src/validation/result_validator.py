"""
Result Validator
Data Quality & Validation Layer (Priority 4)

Validates processing results and output quality:
- Match result consistency validation
- Confidence score calibration
- Reasoning quality assessment
- Cross-reference validation
- Historical consistency checks
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class ResultValidator:
    """Comprehensive result validation system for processing outputs."""

    def __init__(self, excel_path: str = None):
        """Initialize the result validator."""
        if excel_path is None:
            excel_path = str(Path(__file__).parent.parent.parent / "FISHER SKP INTERCHANGE 20260302.xlsx")

        self.excel_path = excel_path

        # Valid result categories
        self.valid_match_results = {'YES', 'LIKELY', 'UNCERTAIN', 'NO'}
        self.valid_fitment_values = {'YES', 'NO', 'UNKNOWN'}
        self.valid_desc_match_values = {'YES', 'NO', 'PARTIAL'}

        # Confidence calibration thresholds
        self.confidence_thresholds = {
            'YES': {'min': 80, 'max': 100, 'expected_min': 85},
            'LIKELY': {'min': 60, 'max': 95, 'expected_min': 65},
            'UNCERTAIN': {'min': 30, 'max': 80, 'expected_min': 35},
            'NO': {'min': 0, 'max': 60, 'expected_min': 10}
        }

        # Quality indicators for match reasons
        self.quality_reason_patterns = {
            'high_quality': [
                r'shared.*oem.*ref',
                r'identical.*part.*number',
                r'same.*manufacturer',
                r'exact.*match',
                r'confirmed.*fitment'
            ],
            'medium_quality': [
                r'similar.*description',
                r'compatible.*spec',
                r'matching.*category',
                r'cross.*reference'
            ],
            'low_quality': [
                r'generic.*match',
                r'possible.*fit',
                r'uncertain.*compatibility'
            ],
            'insufficient': [
                r'^.{0,10}$',  # Very short explanations
                r'no.*reason',
                r'unknown',
                r'n/a'
            ]
        }

        # Historical result tracking for consistency
        self.result_history = defaultdict(list)
        self.consistency_cache = {}

        # Validation statistics
        self.validation_stats = {
            'total_results_validated': 0,
            'confidence_mismatches': 0,
            'reasoning_quality_issues': 0,
            'consistency_violations': 0,
            'last_validation': None
        }

        print("[RESULT_VALIDATOR] Initialized with comprehensive result validation rules")

    def validate_result(self, result_data: Dict, context_data: Optional[Dict] = None) -> Dict:
        """Validate a single processing result."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'quality_score': 1.0,
            'validation_details': {}
        }

        try:
            # Validate basic structure
            structure_validation = self._validate_result_structure(result_data)
            validation_result['validation_details']['structure'] = structure_validation
            if not structure_validation['valid']:
                validation_result['valid'] = False
                validation_result['errors'].extend(structure_validation['errors'])
            validation_result['warnings'].extend(structure_validation['warnings'])

            # Validate confidence calibration
            confidence_validation = self._validate_confidence_calibration(result_data)
            validation_result['validation_details']['confidence'] = confidence_validation
            if not confidence_validation['valid']:
                validation_result['errors'].extend(confidence_validation['errors'])
            validation_result['warnings'].extend(confidence_validation['warnings'])

            # Validate reasoning quality
            reasoning_validation = self._validate_reasoning_quality(result_data)
            validation_result['validation_details']['reasoning'] = reasoning_validation
            validation_result['warnings'].extend(reasoning_validation['warnings'])

            # Validate consistency with context
            if context_data:
                consistency_validation = self._validate_consistency(result_data, context_data)
                validation_result['validation_details']['consistency'] = consistency_validation
                validation_result['warnings'].extend(consistency_validation['warnings'])

            # Validate cross-references if available
            if 'oem_refs' in result_data or (context_data and 'oem_refs' in context_data):
                oem_validation = self._validate_oem_consistency(result_data, context_data)
                validation_result['validation_details']['oem_consistency'] = oem_validation
                validation_result['warnings'].extend(oem_validation['warnings'])

            # Calculate overall quality score
            validation_result['quality_score'] = self._calculate_result_quality_score(
                validation_result['validation_details']
            )

            # Update statistics
            self._update_validation_statistics(validation_result)

        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Error validating result: {str(e)}")

        return validation_result

    def _validate_result_structure(self, result_data: Dict) -> Dict:
        """Validate the basic structure of result data."""
        result = {'valid': True, 'errors': [], 'warnings': []}

        # Required fields
        required_fields = ['match_result', 'confidence', 'match_reason']
        for field in required_fields:
            if field not in result_data:
                result['valid'] = False
                result['errors'].append(f"Missing required field: {field}")

        # Validate match_result
        match_result = result_data.get('match_result')
        if match_result and match_result not in self.valid_match_results:
            result['valid'] = False
            result['errors'].append(f"Invalid match result: {match_result}")

        # Validate confidence range
        confidence = result_data.get('confidence')
        if confidence is not None:
            try:
                conf_value = int(confidence)
                if not (0 <= conf_value <= 100):
                    result['valid'] = False
                    result['errors'].append(f"Confidence out of range: {conf_value}")
            except (ValueError, TypeError):
                result['valid'] = False
                result['errors'].append("Confidence must be an integer")

        # Validate optional fields
        fitment = result_data.get('fitment_match')
        if fitment and fitment not in self.valid_fitment_values:
            result['warnings'].append(f"Unusual fitment value: {fitment}")

        desc_match = result_data.get('desc_match')
        if desc_match and desc_match not in self.valid_desc_match_values:
            result['warnings'].append(f"Unusual description match value: {desc_match}")

        return result

    def _validate_confidence_calibration(self, result_data: Dict) -> Dict:
        """Validate confidence score calibration against match result."""
        result = {'valid': True, 'errors': [], 'warnings': []}

        match_result = result_data.get('match_result')
        confidence = result_data.get('confidence')

        if not match_result or confidence is None:
            return result

        try:
            conf_value = int(confidence)
            thresholds = self.confidence_thresholds.get(match_result, {})

            if not thresholds:
                return result

            # Check if confidence is in expected range
            if conf_value < thresholds.get('min', 0) or conf_value > thresholds.get('max', 100):
                result['errors'].append(
                    f"Confidence {conf_value} out of range for {match_result} "
                    f"(expected: {thresholds['min']}-{thresholds['max']})"
                )

            # Check if confidence meets quality expectations
            elif conf_value < thresholds.get('expected_min', thresholds['min']):
                result['warnings'].append(
                    f"Low confidence {conf_value} for {match_result} result "
                    f"(expected ≥{thresholds['expected_min']})"
                )

        except (ValueError, TypeError):
            result['errors'].append("Could not validate confidence calibration - invalid confidence value")

        return result

    def _validate_reasoning_quality(self, result_data: Dict) -> Dict:
        """Validate the quality of match reasoning."""
        result = {'valid': True, 'errors': [], 'warnings': []}

        match_reason = result_data.get('match_reason', '')
        if not match_reason:
            result['warnings'].append("Missing or empty match reason")
            return result

        reason_text = str(match_reason).lower()

        # Check reasoning quality based on patterns
        quality_level = None
        for level, patterns in self.quality_reason_patterns.items():
            for pattern in patterns:
                if re.search(pattern, reason_text):
                    quality_level = level
                    break
            if quality_level:
                break

        if quality_level == 'insufficient':
            result['warnings'].append("Match reason appears insufficient or generic")
        elif quality_level == 'low_quality':
            result['warnings'].append("Match reason quality could be improved")
        elif quality_level is None:
            result['warnings'].append("Match reason doesn't follow recognized patterns")

        # Check reason length and detail
        if len(reason_text) < 10:
            result['warnings'].append("Match reason is very short")
        elif len(reason_text) > 200:
            result['warnings'].append("Match reason is unusually long")

        # Check for specific quality indicators
        quality_indicators = ['oem', 'part number', 'specification', 'fitment', 'manufacturer']
        indicators_found = sum(1 for indicator in quality_indicators if indicator in reason_text)

        if indicators_found == 0:
            result['warnings'].append("Match reason lacks specific technical details")

        return result

    def _validate_consistency(self, result_data: Dict, context_data: Dict) -> Dict:
        """Validate result consistency with input context."""
        result = {'valid': True, 'errors': [], 'warnings': []}

        try:
            # Create consistency key for tracking
            brand = context_data.get('current_supplier', '')
            part_type = context_data.get('part_type', '')
            consistency_key = f"{brand}_{part_type}"

            # Store this result for future consistency checks
            if consistency_key not in self.result_history:
                self.result_history[consistency_key] = []

            current_result = {
                'match_result': result_data.get('match_result'),
                'confidence': result_data.get('confidence'),
                'timestamp': datetime.now().isoformat()
            }

            # Check against historical results for similar parts
            if len(self.result_history[consistency_key]) > 0:
                similar_results = [
                    r for r in self.result_history[consistency_key]
                    if r.get('match_result') == current_result['match_result']
                ]

                if similar_results:
                    # Calculate confidence deviation from historical average
                    historical_confidences = [r.get('confidence', 0) for r in similar_results]
                    avg_confidence = sum(historical_confidences) / len(historical_confidences)
                    current_confidence = current_result.get('confidence', 0)

                    if abs(current_confidence - avg_confidence) > 20:
                        result['warnings'].append(
                            f"Confidence {current_confidence} deviates significantly from "
                            f"historical average {avg_confidence:.1f} for {brand} {part_type}"
                        )

            # Add to history (keep last 50 results)
            self.result_history[consistency_key].append(current_result)
            if len(self.result_history[consistency_key]) > 50:
                self.result_history[consistency_key] = self.result_history[consistency_key][-50:]

        except Exception as e:
            result['warnings'].append(f"Could not validate consistency: {str(e)}")

        return result

    def _validate_oem_consistency(self, result_data: Dict, context_data: Optional[Dict] = None) -> Dict:
        """Validate OEM reference consistency in results."""
        result = {'valid': True, 'errors': [], 'warnings': []}

        try:
            match_result = result_data.get('match_result')
            match_reason = result_data.get('match_reason', '').lower()

            # Check if result claims OEM match but reasoning doesn't support it
            if match_result in ['YES', 'LIKELY']:
                if 'oem' in match_reason or 'shared' in match_reason:
                    # Good - reasoning mentions OEM
                    pass
                else:
                    # Check if context has OEM data that should be mentioned
                    if context_data:
                        oem_refs = context_data.get('oem_refs', [])
                        if oem_refs and len(oem_refs) > 1:
                            result['warnings'].append(
                                "High confidence result without OEM reference explanation"
                            )

            elif match_result == 'NO':
                # Check if reasoning explains why OEM references don't match
                if context_data:
                    oem_refs = context_data.get('oem_refs', [])
                    if oem_refs and 'oem' not in match_reason:
                        result['warnings'].append(
                            "NO result without OEM comparison explanation"
                        )

        except Exception as e:
            result['warnings'].append(f"Could not validate OEM consistency: {str(e)}")

        return result

    def _calculate_result_quality_score(self, validation_details: Dict) -> float:
        """Calculate overall result quality score."""
        try:
            scores = []

            # Structure quality (0.3 weight)
            structure_score = 1.0 if validation_details.get('structure', {}).get('valid', False) else 0.0
            scores.append(structure_score * 0.3)

            # Confidence calibration (0.3 weight)
            confidence_valid = validation_details.get('confidence', {}).get('valid', False)
            confidence_warnings = len(validation_details.get('confidence', {}).get('warnings', []))
            confidence_score = 1.0 if confidence_valid and confidence_warnings == 0 else (0.7 if confidence_valid else 0.0)
            scores.append(confidence_score * 0.3)

            # Reasoning quality (0.25 weight)
            reasoning_warnings = len(validation_details.get('reasoning', {}).get('warnings', []))
            reasoning_score = max(0.0, 1.0 - (reasoning_warnings * 0.2))
            scores.append(reasoning_score * 0.25)

            # Consistency (0.15 weight)
            consistency_warnings = len(validation_details.get('consistency', {}).get('warnings', []))
            consistency_score = max(0.0, 1.0 - (consistency_warnings * 0.3))
            scores.append(consistency_score * 0.15)

            return sum(scores)

        except Exception as e:
            print(f"Warning: Error calculating quality score: {e}")
            return 0.5

    def _update_validation_statistics(self, validation_result: Dict):
        """Update validation statistics."""
        self.validation_stats['total_results_validated'] += 1

        if not validation_result['valid']:
            self.validation_stats['consistency_violations'] += 1

        # Count specific issue types
        details = validation_result.get('validation_details', {})

        confidence_issues = details.get('confidence', {}).get('warnings', [])
        if confidence_issues:
            self.validation_stats['confidence_mismatches'] += 1

        reasoning_issues = details.get('reasoning', {}).get('warnings', [])
        if reasoning_issues:
            self.validation_stats['reasoning_quality_issues'] += 1

    def validate_result_batch(self, results: List[Dict], contexts: Optional[List[Dict]] = None) -> Dict:
        """Validate a batch of results for consistency and quality."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'batch_statistics': {},
            'quality_distribution': {},
            'consistency_analysis': {}
        }

        try:
            if not results:
                validation_result['valid'] = False
                validation_result['errors'].append("Empty results batch")
                return validation_result

            individual_scores = []
            match_results = []
            confidence_scores = []

            # Validate each result individually
            for i, result in enumerate(results):
                context = contexts[i] if contexts and i < len(contexts) else None
                individual_validation = self.validate_result(result, context)

                individual_scores.append(individual_validation['quality_score'])
                match_results.append(result.get('match_result'))

                confidence = result.get('confidence')
                if confidence is not None:
                    try:
                        confidence_scores.append(int(confidence))
                    except (ValueError, TypeError):
                        pass

                # Collect errors and warnings
                validation_result['errors'].extend(individual_validation['errors'])
                validation_result['warnings'].extend(individual_validation['warnings'])

            # Calculate batch statistics
            validation_result['batch_statistics'] = {
                'total_results': len(results),
                'average_quality_score': sum(individual_scores) / len(individual_scores),
                'min_quality_score': min(individual_scores),
                'max_quality_score': max(individual_scores),
                'match_result_distribution': dict(Counter(match_results)),
                'average_confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                'confidence_std_dev': self._calculate_std_dev(confidence_scores) if len(confidence_scores) > 1 else 0
            }

            # Quality distribution analysis
            validation_result['quality_distribution'] = {
                'high_quality': sum(1 for score in individual_scores if score >= 0.8),
                'medium_quality': sum(1 for score in individual_scores if 0.5 <= score < 0.8),
                'low_quality': sum(1 for score in individual_scores if score < 0.5)
            }

            # Consistency analysis
            validation_result['consistency_analysis'] = self._analyze_batch_consistency(results)

        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Error validating result batch: {str(e)}")

        return validation_result

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _analyze_batch_consistency(self, results: List[Dict]) -> Dict:
        """Analyze consistency patterns in a batch of results."""
        analysis = {
            'confidence_consistency': 'good',
            'reasoning_patterns': {},
            'anomalies': []
        }

        try:
            # Group by match result and analyze confidence patterns
            result_groups = defaultdict(list)
            for result in results:
                match_result = result.get('match_result')
                confidence = result.get('confidence')
                if match_result and confidence is not None:
                    try:
                        result_groups[match_result].append(int(confidence))
                    except (ValueError, TypeError):
                        pass

            # Check confidence consistency within each result type
            for match_result, confidences in result_groups.items():
                if len(confidences) > 1:
                    std_dev = self._calculate_std_dev(confidences)
                    if std_dev > 25:  # High variance in confidence
                        analysis['anomalies'].append(
                            f"High confidence variance for {match_result} results (σ={std_dev:.1f})"
                        )

            # Analyze reasoning patterns
            reasoning_lengths = [len(str(r.get('match_reason', ''))) for r in results]
            if reasoning_lengths:
                avg_length = sum(reasoning_lengths) / len(reasoning_lengths)
                analysis['reasoning_patterns']['average_length'] = avg_length

                if avg_length < 20:
                    analysis['anomalies'].append("Very short reasoning explanations on average")

        except Exception as e:
            analysis['anomalies'].append(f"Error analyzing batch consistency: {str(e)}")

        return analysis

    def get_validation_report(self) -> Dict:
        """Generate comprehensive result validation report."""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'validation_statistics': self.validation_stats.copy(),
                'validation_rules': {
                    'valid_match_results': list(self.valid_match_results),
                    'confidence_thresholds': self.confidence_thresholds,
                    'quality_indicators': {
                        'reasoning_patterns': len(self.quality_reason_patterns),
                        'oem_consistency_checks': True,
                        'historical_consistency': True
                    }
                },
                'quality_metrics': self._calculate_validation_metrics(),
                'consistency_tracking': {
                    'tracked_categories': len(self.result_history),
                    'total_historical_results': sum(len(results) for results in self.result_history.values())
                },
                'recommendations': self._generate_result_validation_recommendations()
            }

            self.validation_stats['last_validation'] = datetime.now().isoformat()

            return report

        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': f"Error generating validation report: {str(e)}",
                'validation_statistics': self.validation_stats.copy()
            }

    def _calculate_validation_metrics(self) -> Dict:
        """Calculate validation performance metrics."""
        total = max(1, self.validation_stats['total_results_validated'])

        return {
            'total_validations': total,
            'confidence_mismatch_rate': self.validation_stats['confidence_mismatches'] / total,
            'reasoning_issue_rate': self.validation_stats['reasoning_quality_issues'] / total,
            'consistency_violation_rate': self.validation_stats['consistency_violations'] / total,
            'overall_quality_rate': 1.0 - (
                (self.validation_stats['confidence_mismatches'] +
                 self.validation_stats['reasoning_quality_issues'] +
                 self.validation_stats['consistency_violations']) / (total * 3)
            )
        }

    def _generate_result_validation_recommendations(self) -> List[str]:
        """Generate recommendations for improving result quality."""
        recommendations = []
        metrics = self._calculate_validation_metrics()

        if metrics['confidence_mismatch_rate'] > 0.15:
            recommendations.append("High confidence calibration errors - review threshold settings")

        if metrics['reasoning_issue_rate'] > 0.25:
            recommendations.append("Reasoning quality issues detected - improve explanation generation")

        if metrics['consistency_violation_rate'] > 0.10:
            recommendations.append("Consistency issues found - review processing logic")

        if metrics['overall_quality_rate'] < 0.7:
            recommendations.append("Overall result quality below standard - comprehensive review needed")

        if metrics['overall_quality_rate'] > 0.9:
            recommendations.append("Excellent result quality - maintain current validation standards")

        if not recommendations:
            recommendations.append("Insufficient validation data for specific recommendations")

        return recommendations

if __name__ == "__main__":
    # Test the result validator
    print("Testing Result Validator...")

    validator = ResultValidator()

    # Test valid result
    print("1. Testing valid result validation...")
    test_result = {
        'match_result': 'YES',
        'confidence': 95,
        'match_reason': 'Shared OEM reference 5273883AD confirms compatibility',
        'fitment_match': 'YES',
        'desc_match': 'YES'
    }

    test_context = {
        'current_supplier': 'ANCHOR',
        'part_type': 'ENGINE MOUNT',
        'oem_refs': ['5273883AD', '7B0199279A']
    }

    result_validation = validator.validate_result(test_result, test_context)
    print(f"   Result valid: {result_validation['valid']}")
    print(f"   Quality score: {result_validation['quality_score']:.3f}")
    print(f"   Warnings: {len(result_validation['warnings'])}")

    # Test batch validation
    print("2. Testing batch validation...")
    test_batch = [test_result] * 3

    batch_validation = validator.validate_result_batch(test_batch, [test_context] * 3)
    print(f"   Batch valid: {batch_validation['valid']}")
    print(f"   Average quality: {batch_validation['batch_statistics']['average_quality_score']:.3f}")

    # Test validation report
    print("3. Testing validation report...")
    report = validator.get_validation_report()
    print(f"   Report sections: {len(report)}")
    print(f"   Recommendations: {len(report.get('recommendations', []))}")

    print("Result Validator test completed.")