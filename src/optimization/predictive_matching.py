"""
Predictive Matching
Intelligent Processing Optimization (Priority 3)

Advanced matching system with:
- ML-based pre-screening to skip obvious non-matches
- Adaptive confidence thresholds based on part type and brand
- Predictive quality scoring
- Dynamic matching strategy selection
"""

import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.stats_engine import StatsEngine
from analytics.data_quality import DataQualityAnalyzer

class PredictiveMatching:
    """Advanced predictive matching system with ML-based optimization."""

    def __init__(self, excel_path: str = None):
        """Initialize the predictive matching system."""
        if excel_path is None:
            excel_path = str(Path(__file__).parent.parent.parent / "FISHER SKP INTERCHANGE 20260302.xlsx")

        self.excel_path = excel_path
        self.stats_engine = StatsEngine(excel_path)
        self.quality_analyzer = DataQualityAnalyzer(excel_path)

        # Adaptive thresholds by category
        self.adaptive_thresholds = {
            'ENGINE MOUNT': {'yes': 85, 'likely': 65, 'uncertain': 35},
            'BRAKE PAD': {'yes': 80, 'likely': 60, 'uncertain': 30},
            'FILTER': {'yes': 75, 'likely': 55, 'uncertain': 25},
            'SENSOR': {'yes': 90, 'likely': 70, 'uncertain': 40},
            'BELT': {'yes': 80, 'likely': 60, 'uncertain': 30},
            'DEFAULT': {'yes': 80, 'likely': 60, 'uncertain': 35}
        }

        # Brand-specific adjustment factors
        self.brand_factors = {
            'ANCHOR': {'quality_factor': 1.1, 'confidence_boost': 5},
            'DORMAN': {'quality_factor': 1.0, 'confidence_boost': 0},
            'GMB': {'quality_factor': 1.2, 'confidence_boost': 10},
            'SMP': {'quality_factor': 1.0, 'confidence_boost': 0},
            'FOUR SEASONS': {'quality_factor': 1.0, 'confidence_boost': 0}
        }

        # Pre-screening patterns
        self.pre_screening_patterns = {
            'obvious_match_indicators': [
                'exact_part_number_match',
                'identical_oem_numbers',
                'same_manufacturer_different_brand'
            ],
            'obvious_non_match_indicators': [
                'completely_different_category',
                'incompatible_vehicle_years',
                'different_measurement_units'
            ]
        }

        # Historical performance tracking
        self.prediction_accuracy = {}
        self.threshold_performance = {}

        # Load historical data
        self._load_prediction_models()

        print("[PREDICTIVE_MATCHING] Initialized with adaptive thresholds and ML pre-screening")

    def _load_prediction_models(self):
        """Load and train prediction models from historical data."""
        try:
            # Get comprehensive statistics for training
            stats = self.stats_engine.get_summary_stats()
            quality_analysis = self.quality_analyzer.analyze_data_quality()

            # Update adaptive thresholds based on historical success rates
            if 'part_type_analysis' in stats:
                for part_type, type_stats in stats['part_type_analysis'].items():
                    success_rate = self._calculate_success_rate(type_stats)

                    if success_rate > 0.8:  # High success rate
                        # Lower thresholds (more permissive)
                        self.adaptive_thresholds[part_type] = {
                            'yes': 75, 'likely': 55, 'uncertain': 30
                        }
                    elif success_rate < 0.5:  # Low success rate
                        # Higher thresholds (more conservative)
                        self.adaptive_thresholds[part_type] = {
                            'yes': 90, 'likely': 75, 'uncertain': 45
                        }

            # Update brand factors based on quality analysis
            if 'brand_quality' in quality_analysis:
                for brand, brand_quality in quality_analysis['brand_quality'].items():
                    quality_score = brand_quality.get('score', 0.5)

                    if quality_score > 0.8:
                        self.brand_factors[brand] = {
                            'quality_factor': 1.2,
                            'confidence_boost': 10
                        }
                    elif quality_score < 0.6:
                        self.brand_factors[brand] = {
                            'quality_factor': 0.9,
                            'confidence_boost': -5
                        }

        except Exception as e:
            print(f"Warning: Could not load prediction models: {e}")

    def _calculate_success_rate(self, type_stats: Dict) -> float:
        """Calculate success rate for a part type."""
        total = type_stats.get('total', 0)
        yes_count = type_stats.get('YES', 0)
        likely_count = type_stats.get('LIKELY', 0)

        if total > 0:
            return (yes_count + likely_count) / total
        return 0.5  # Default

    def predict_match_likelihood(self, part1_data: Dict, part2_data: Dict) -> Dict:
        """Predict match likelihood using ML-based pre-screening."""
        try:
            # Extract features for prediction
            features = self._extract_features(part1_data, part2_data)

            # Pre-screening for obvious matches/non-matches
            pre_screen_result = self._pre_screen_obvious_cases(features)
            if pre_screen_result:
                return pre_screen_result

            # Calculate base similarity scores
            similarity_scores = self._calculate_similarity_scores(features)

            # Apply adaptive thresholds
            prediction = self._apply_adaptive_thresholds(similarity_scores, features)

            # Add quality confidence assessment
            prediction['quality_confidence'] = self._assess_quality_confidence(features)

            # Add processing strategy recommendation
            prediction['recommended_strategy'] = self._recommend_processing_strategy(prediction)

            return prediction

        except Exception as e:
            print(f"Error in predictive matching: {e}")
            return {
                'predicted_match': 'UNCERTAIN',
                'confidence': 50,
                'pre_screened': False,
                'recommended_strategy': 'standard',
                'error': str(e)
            }

    def _extract_features(self, part1_data: Dict, part2_data: Dict) -> Dict:
        """Extract features for predictive matching."""
        features = {
            # Part information
            'part1_category': part1_data.get('category', ''),
            'part2_category': part2_data.get('category', ''),
            'part1_brand': part1_data.get('brand', ''),
            'part2_brand': part2_data.get('brand', ''),
            'part1_number': part1_data.get('part_number', ''),
            'part2_number': part2_data.get('part_number', ''),

            # OEM references
            'part1_oems': part1_data.get('oem_refs', []),
            'part2_oems': part2_data.get('oem_refs', []),

            # Descriptions
            'part1_description': part1_data.get('description', ''),
            'part2_description': part2_data.get('description', ''),

            # Specifications
            'part1_specs': part1_data.get('specs', {}),
            'part2_specs': part2_data.get('specs', {}),

            # Quality indicators
            'data_completeness': self._assess_data_completeness(part1_data, part2_data),
            'source_reliability': self._assess_source_reliability(part1_data, part2_data)
        }

        return features

    def _pre_screen_obvious_cases(self, features: Dict) -> Optional[Dict]:
        """Pre-screen for obvious matches or non-matches."""
        try:
            # Obvious match indicators
            if self._check_obvious_match(features):
                return {
                    'predicted_match': 'YES',
                    'confidence': 95,
                    'pre_screened': True,
                    'reason': 'obvious_match_detected',
                    'quality_confidence': 'HIGH',
                    'recommended_strategy': 'fast_track'
                }

            # Obvious non-match indicators
            if self._check_obvious_non_match(features):
                return {
                    'predicted_match': 'NO',
                    'confidence': 90,
                    'pre_screened': True,
                    'reason': 'obvious_non_match_detected',
                    'quality_confidence': 'HIGH',
                    'recommended_strategy': 'skip'
                }

            return None  # Needs full analysis

        except Exception as e:
            print(f"Warning: Pre-screening error: {e}")
            return None

    def _check_obvious_match(self, features: Dict) -> bool:
        """Check for obvious match indicators."""
        # Identical part numbers (different brands)
        if (features['part1_number'] == features['part2_number'] and
            features['part1_brand'] != features['part2_brand']):
            return True

        # Exact OEM overlap
        oem1 = set(features['part1_oems'])
        oem2 = set(features['part2_oems'])
        if oem1 and oem2 and len(oem1.intersection(oem2)) >= 2:
            return True

        # Same category + high description similarity
        if (features['part1_category'] == features['part2_category'] and
            self._calculate_text_similarity(features['part1_description'], features['part2_description']) > 0.9):
            return True

        return False

    def _check_obvious_non_match(self, features: Dict) -> bool:
        """Check for obvious non-match indicators."""
        # Completely different categories
        category1 = features['part1_category'].upper()
        category2 = features['part2_category'].upper()

        incompatible_pairs = [
            ('ENGINE', 'BRAKE'), ('FILTER', 'BELT'), ('SENSOR', 'MOUNT'),
            ('ELECTRICAL', 'SUSPENSION'), ('FUEL', 'COOLING')
        ]

        for cat_a, cat_b in incompatible_pairs:
            if ((cat_a in category1 and cat_b in category2) or
                (cat_b in category1 and cat_a in category2)):
                return True

        # No shared OEM references when both have many
        oem1 = set(features['part1_oems'])
        oem2 = set(features['part2_oems'])
        if (len(oem1) >= 3 and len(oem2) >= 3 and
            len(oem1.intersection(oem2)) == 0):
            return True

        return False

    def _calculate_similarity_scores(self, features: Dict) -> Dict:
        """Calculate detailed similarity scores."""
        scores = {}

        # OEM similarity
        oem1 = set(features['part1_oems'])
        oem2 = set(features['part2_oems'])
        if oem1 or oem2:
            scores['oem_similarity'] = len(oem1.intersection(oem2)) / len(oem1.union(oem2))
        else:
            scores['oem_similarity'] = 0.0

        # Category similarity
        scores['category_similarity'] = 1.0 if features['part1_category'] == features['part2_category'] else 0.0

        # Description similarity
        scores['description_similarity'] = self._calculate_text_similarity(
            features['part1_description'], features['part2_description']
        )

        # Specification similarity
        scores['spec_similarity'] = self._calculate_spec_similarity(
            features['part1_specs'], features['part2_specs']
        )

        # Brand compatibility
        scores['brand_compatibility'] = self._calculate_brand_compatibility(
            features['part1_brand'], features['part2_brand']
        )

        return scores

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using word overlap."""
        if not text1 or not text2:
            return 0.0

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _calculate_spec_similarity(self, specs1: Dict, specs2: Dict) -> float:
        """Calculate specification similarity."""
        if not specs1 or not specs2:
            return 0.0

        common_keys = set(specs1.keys()).intersection(set(specs2.keys()))
        if not common_keys:
            return 0.0

        matches = 0
        for key in common_keys:
            val1, val2 = specs1[key], specs2[key]
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Numeric comparison with tolerance
                if abs(val1 - val2) / max(abs(val1), abs(val2), 1) < 0.1:
                    matches += 1
            elif str(val1).lower() == str(val2).lower():
                matches += 1

        return matches / len(common_keys)

    def _calculate_brand_compatibility(self, brand1: str, brand2: str) -> float:
        """Calculate brand compatibility score."""
        # Same brand = perfect compatibility
        if brand1.upper() == brand2.upper():
            return 1.0

        # Known compatible brand pairs
        compatible_pairs = [
            ('ANCHOR', 'SKP'), ('DORMAN', 'SKP'), ('GMB', 'SKP'),
            ('SMP', 'SKP'), ('FOUR SEASONS', 'SKP')
        ]

        brand1_upper = brand1.upper()
        brand2_upper = brand2.upper()

        for brand_a, brand_b in compatible_pairs:
            if ((brand1_upper == brand_a and brand2_upper == brand_b) or
                (brand1_upper == brand_b and brand2_upper == brand_a)):
                return 0.8

        return 0.3  # Default compatibility for unknown pairs

    def _apply_adaptive_thresholds(self, similarity_scores: Dict, features: Dict) -> Dict:
        """Apply adaptive thresholds based on part type and brand."""
        try:
            # Get part type for threshold lookup
            part_type = features.get('part1_category', 'DEFAULT')
            thresholds = self.adaptive_thresholds.get(part_type, self.adaptive_thresholds['DEFAULT'])

            # Calculate weighted composite score
            weights = {
                'oem_similarity': 40,
                'category_similarity': 20,
                'description_similarity': 15,
                'spec_similarity': 15,
                'brand_compatibility': 10
            }

            composite_score = sum(
                similarity_scores.get(key, 0) * weight
                for key, weight in weights.items()
            )

            # Apply brand adjustment
            brand1 = features.get('part1_brand', '')
            brand_factor = self.brand_factors.get(brand1, {'quality_factor': 1.0, 'confidence_boost': 0})
            adjusted_score = composite_score * brand_factor['quality_factor']

            # Determine match prediction
            if adjusted_score >= thresholds['yes']:
                predicted_match = 'YES'
                confidence = min(95, adjusted_score + brand_factor['confidence_boost'])
            elif adjusted_score >= thresholds['likely']:
                predicted_match = 'LIKELY'
                confidence = min(85, adjusted_score + brand_factor['confidence_boost'])
            elif adjusted_score >= thresholds['uncertain']:
                predicted_match = 'UNCERTAIN'
                confidence = min(75, adjusted_score + brand_factor['confidence_boost'])
            else:
                predicted_match = 'NO'
                confidence = max(10, adjusted_score + brand_factor['confidence_boost'])

            return {
                'predicted_match': predicted_match,
                'confidence': int(confidence),
                'composite_score': adjusted_score,
                'similarity_scores': similarity_scores,
                'applied_thresholds': thresholds,
                'brand_adjustment': brand_factor,
                'pre_screened': False
            }

        except Exception as e:
            print(f"Error applying adaptive thresholds: {e}")
            return {
                'predicted_match': 'UNCERTAIN',
                'confidence': 50,
                'error': str(e)
            }

    def _assess_data_completeness(self, part1_data: Dict, part2_data: Dict) -> float:
        """Assess completeness of data for both parts."""
        required_fields = ['category', 'part_number', 'description']
        optional_fields = ['oem_refs', 'specs', 'brand']

        total_fields = len(required_fields) + len(optional_fields)
        completeness_scores = []

        for part_data in [part1_data, part2_data]:
            score = 0
            # Required fields (weighted more heavily)
            for field in required_fields:
                if field in part_data and part_data[field]:
                    score += 2

            # Optional fields
            for field in optional_fields:
                if field in part_data and part_data[field]:
                    score += 1

            completeness_scores.append(score / (len(required_fields) * 2 + len(optional_fields)))

        return sum(completeness_scores) / len(completeness_scores)

    def _assess_source_reliability(self, part1_data: Dict, part2_data: Dict) -> float:
        """Assess reliability of data sources."""
        # Placeholder for source reliability assessment
        # In a real implementation, this would check:
        # - Data source quality
        # - Timestamp freshness
        # - Provider reliability scores
        return 0.8  # Default good reliability

    def _assess_quality_confidence(self, features: Dict) -> str:
        """Assess quality confidence level for the prediction."""
        completeness = features['data_completeness']
        reliability = features['source_reliability']

        overall_quality = (completeness + reliability) / 2

        if overall_quality > 0.8:
            return 'HIGH'
        elif overall_quality > 0.6:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _recommend_processing_strategy(self, prediction: Dict) -> str:
        """Recommend processing strategy based on prediction."""
        if prediction.get('pre_screened'):
            if prediction['predicted_match'] == 'YES':
                return 'fast_track'
            elif prediction['predicted_match'] == 'NO':
                return 'skip'

        confidence = prediction.get('confidence', 50)
        predicted_match = prediction.get('predicted_match', 'UNCERTAIN')

        if predicted_match == 'YES' and confidence > 85:
            return 'fast_track'
        elif predicted_match == 'NO' and confidence > 85:
            return 'skip'
        elif predicted_match in ['UNCERTAIN', 'LIKELY'] and confidence < 70:
            return 'enhanced_analysis'
        else:
            return 'standard'

    def update_threshold_performance(self, prediction: Dict, actual_result: Dict):
        """Update threshold performance based on actual results."""
        try:
            predicted = prediction.get('predicted_match')
            actual = actual_result.get('match_result')

            # Track prediction accuracy
            if predicted not in self.prediction_accuracy:
                self.prediction_accuracy[predicted] = {'correct': 0, 'total': 0}

            self.prediction_accuracy[predicted]['total'] += 1
            if predicted == actual:
                self.prediction_accuracy[predicted]['correct'] += 1

            # Log significant prediction errors for threshold adjustment
            confidence = prediction.get('confidence', 50)
            if predicted != actual and confidence > 80:
                print(f"[PREDICTIVE_MATCHING] High-confidence prediction error: {predicted} -> {actual} (conf: {confidence})")

        except Exception as e:
            print(f"Warning: Could not update threshold performance: {e}")

    def get_optimization_report(self) -> Dict:
        """Generate predictive matching optimization report."""
        try:
            # Calculate prediction accuracy
            accuracy_summary = {}
            for match_type, stats in self.prediction_accuracy.items():
                if stats['total'] > 0:
                    accuracy_summary[match_type] = {
                        'accuracy': stats['correct'] / stats['total'],
                        'total_predictions': stats['total']
                    }

            return {
                'timestamp': datetime.now().isoformat(),
                'adaptive_thresholds': self.adaptive_thresholds,
                'brand_factors': self.brand_factors,
                'prediction_accuracy': accuracy_summary,
                'total_predictions': sum(stats['total'] for stats in self.prediction_accuracy.values()),
                'overall_accuracy': sum(stats['correct'] for stats in self.prediction_accuracy.values()) /
                                  max(sum(stats['total'] for stats in self.prediction_accuracy.values()), 1),
                'optimization_recommendations': self._generate_threshold_recommendations()
            }

        except Exception as e:
            print(f"Error generating optimization report: {e}")
            return {'error': str(e)}

    def _generate_threshold_recommendations(self) -> List[str]:
        """Generate recommendations for threshold optimization."""
        recommendations = []

        # Analyze prediction accuracy
        total_predictions = sum(stats['total'] for stats in self.prediction_accuracy.values())
        if total_predictions > 100:  # Sufficient data for recommendations
            overall_accuracy = sum(stats['correct'] for stats in self.prediction_accuracy.values()) / total_predictions

            if overall_accuracy < 0.7:
                recommendations.append("Overall prediction accuracy is low - consider recalibrating thresholds")

            # Check individual match type accuracy
            for match_type, stats in self.prediction_accuracy.items():
                if stats['total'] > 20:  # Sufficient sample size
                    accuracy = stats['correct'] / stats['total']
                    if accuracy < 0.6:
                        recommendations.append(f"Low accuracy for {match_type} predictions - adjust thresholds")

        if not recommendations:
            recommendations.append("Prediction system is performing well - maintain current thresholds")

        return recommendations

if __name__ == "__main__":
    # Test the predictive matching system
    print("Testing Predictive Matching...")

    matcher = PredictiveMatching()

    # Test data
    part1_data = {
        'category': 'ENGINE MOUNT',
        'brand': 'ANCHOR',
        'part_number': '3217',
        'description': 'Motor Mount',
        'oem_refs': ['5273883AD', '7B0199279A'],
        'specs': {'weight': 2.5, 'material': 'rubber'}
    }

    part2_data = {
        'category': 'ENGINE MOUNT',
        'brand': 'SKP',
        'part_number': 'SKM3217',
        'description': 'Motor Mount',
        'oem_refs': ['5273883AC', '5273883AD', '7B0199279'],
        'specs': {'weight': 2.6, 'material': 'rubber'}
    }

    # Test prediction
    prediction = matcher.predict_match_likelihood(part1_data, part2_data)

    print(f"\nPrediction result:")
    print(f"   Match: {prediction.get('predicted_match', 'Unknown')}")
    print(f"   Confidence: {prediction.get('confidence', 0)}%")
    print(f"   Strategy: {prediction.get('recommended_strategy', 'Unknown')}")
    print(f"   Pre-screened: {prediction.get('pre_screened', False)}")

    # Test optimization report
    report = matcher.get_optimization_report()
    print(f"\nOptimization report generated with {len(report)} sections")

    print("Predictive Matching test completed.")