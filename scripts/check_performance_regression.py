#!/usr/bin/env python3
"""
Performance regression detection script.

Compares current benchmark results against baselines to detect performance
regressions and generate actionable reports for CI/CD pipelines.
"""

import json
import argparse
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RegressionResult:
    """Result of regression analysis."""
    function_name: str
    baseline_ops_per_sec: float
    current_ops_per_sec: float
    regression_percent: float
    severity: str
    threshold_exceeded: bool


class PerformanceRegressionChecker:
    """Analyzes performance benchmark results for regressions."""
    
    def __init__(self, regression_threshold: float = 0.15):
        """
        Initialize regression checker.
        
        Args:
            regression_threshold: Percentage threshold for regression detection (0.15 = 15%)
        """
        self.regression_threshold = regression_threshold
        self.severity_thresholds = {
            'low': 0.10,      # 10% regression
            'medium': 0.25,   # 25% regression
            'high': 0.50,     # 50% regression
            'critical': 1.0   # 100% regression
        }
    
    def load_benchmark_data(self, file_path: Path) -> Dict[str, Any]:
        """Load benchmark data from JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading benchmark data from {file_path}: {e}")
            return {}
    
    def extract_performance_metrics(self, benchmark_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Extract performance metrics from benchmark data."""
        metrics = {}
        
        # Handle different benchmark data formats
        if 'benchmarks' in benchmark_data:
            # pytest-benchmark format
            for benchmark in benchmark_data['benchmarks']:
                name = benchmark['name']
                stats = benchmark['stats']
                metrics[name] = {
                    'ops_per_sec': 1.0 / stats['mean'] if stats['mean'] > 0 else 0,
                    'mean_time': stats['mean'],
                    'min_time': stats['min'],
                    'max_time': stats['max'],
                    'stddev': stats['stddev']
                }
        elif 'results' in benchmark_data:
            # Custom benchmark format
            for result in benchmark_data['results']:
                name = result['test_name']
                metrics[name] = {
                    'ops_per_sec': result.get('operations_per_second', 0),
                    'mean_time': result.get('avg_time_per_op', 0),
                    'success_rate': result.get('success_rate', 1.0),
                    'memory_mb': result.get('memory_used_mb', 0)
                }
        else:
            # Direct format
            for name, data in benchmark_data.items():
                if isinstance(data, dict) and 'operations_per_second' in data:
                    metrics[name] = data
        
        return metrics
    
    def calculate_regression(self, baseline_ops: float, current_ops: float) -> float:
        """Calculate regression percentage."""
        if baseline_ops <= 0:
            return 0.0
        
        return (baseline_ops - current_ops) / baseline_ops
    
    def determine_severity(self, regression_percent: float) -> str:
        """Determine severity level based on regression percentage."""
        abs_regression = abs(regression_percent)
        
        if abs_regression >= self.severity_thresholds['critical']:
            return 'critical'
        elif abs_regression >= self.severity_thresholds['high']:
            return 'high'
        elif abs_regression >= self.severity_thresholds['medium']:
            return 'medium'
        elif abs_regression >= self.severity_thresholds['low']:
            return 'low'
        else:
            return 'none'
    
    def analyze_regressions(self, baseline_metrics: Dict[str, Dict[str, float]], 
                          current_metrics: Dict[str, Dict[str, float]]) -> List[RegressionResult]:
        """Analyze benchmark results for performance regressions."""
        regressions = []
        
        for function_name in current_metrics:
            if function_name not in baseline_metrics:
                continue  # Skip new functions
            
            baseline_data = baseline_metrics[function_name]
            current_data = current_metrics[function_name]
            
            baseline_ops = baseline_data.get('ops_per_sec', 0)
            current_ops = current_data.get('ops_per_sec', 0)
            
            if baseline_ops <= 0 or current_ops <= 0:
                continue  # Skip invalid data
            
            regression_percent = self.calculate_regression(baseline_ops, current_ops)
            severity = self.determine_severity(regression_percent)
            threshold_exceeded = abs(regression_percent) > self.regression_threshold
            
            # Only report significant regressions
            if threshold_exceeded and regression_percent > 0:
                regressions.append(RegressionResult(
                    function_name=function_name,
                    baseline_ops_per_sec=baseline_ops,
                    current_ops_per_sec=current_ops,
                    regression_percent=regression_percent,
                    severity=severity,
                    threshold_exceeded=threshold_exceeded
                ))
        
        # Sort by regression severity and percentage
        severity_order = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'none': 0}
        regressions.sort(key=lambda x: (severity_order[x.severity], x.regression_percent), reverse=True)
        
        return regressions
    
    def generate_report(self, regressions: List[RegressionResult], 
                       baseline_path: str, current_path: str) -> Dict[str, Any]:
        """Generate comprehensive regression report."""
        report = {
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'baseline_file': baseline_path,
                'current_file': current_path,
                'regression_threshold': self.regression_threshold,
                'total_functions_analyzed': len(regressions) if regressions else 0
            },
            'summary': {
                'total_regressions': len(regressions),
                'critical_regressions': len([r for r in regressions if r.severity == 'critical']),
                'high_regressions': len([r for r in regressions if r.severity == 'high']),
                'medium_regressions': len([r for r in regressions if r.severity == 'medium']),
                'low_regressions': len([r for r in regressions if r.severity == 'low']),
                'has_blocking_regressions': any(r.severity in ['critical', 'high'] for r in regressions)
            },
            'regressions': []
        }
        
        for regression in regressions:
            report['regressions'].append({
                'function_name': regression.function_name,
                'baseline_ops_per_sec': regression.baseline_ops_per_sec,
                'current_ops_per_sec': regression.current_ops_per_sec,
                'regression_percent': regression.regression_percent * 100,  # Convert to percentage
                'severity': regression.severity,
                'performance_impact': f"{regression.regression_percent:.1%} slower",
                'recommendation': self._generate_recommendation(regression)
            })
        
        return report
    
    def _generate_recommendation(self, regression: RegressionResult) -> str:
        """Generate recommendation based on regression severity."""
        if regression.severity == 'critical':
            return "URGENT: Critical performance regression detected. Investigate immediately."
        elif regression.severity == 'high':
            return "High priority: Significant performance degradation requires investigation."
        elif regression.severity == 'medium':
            return "Medium priority: Performance regression should be addressed in next iteration."
        elif regression.severity == 'low':
            return "Low priority: Minor performance regression, monitor for trends."
        else:
            return "No action required."


def main():
    parser = argparse.ArgumentParser(description='Detect performance regressions in benchmark results')
    parser.add_argument('--current', required=True, help='Path to current benchmark results JSON file')
    parser.add_argument('--baseline', help='Path to baseline benchmark results JSON file')
    parser.add_argument('--threshold', type=float, default=0.15, 
                       help='Regression threshold (default: 0.15 = 15%)')
    parser.add_argument('--output', help='Path to output regression report JSON file')
    parser.add_argument('--fail-on-regression', action='store_true',
                       help='Exit with non-zero code if regressions are detected')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Initialize regression checker
    checker = PerformanceRegressionChecker(regression_threshold=args.threshold)
    
    # Load current benchmark data
    current_path = Path(args.current)
    if not current_path.exists():
        print(f"Error: Current benchmark file not found: {current_path}")
        sys.exit(1)
    
    current_data = checker.load_benchmark_data(current_path)
    if not current_data:
        print("Error: Failed to load current benchmark data")
        sys.exit(1)
    
    current_metrics = checker.extract_performance_metrics(current_data)
    
    # Load baseline data if provided
    if args.baseline:
        baseline_path = Path(args.baseline)
        if not baseline_path.exists():
            print(f"Warning: Baseline file not found: {baseline_path}")
            print("Skipping regression analysis - no baseline to compare against")
            sys.exit(0)
        
        baseline_data = checker.load_benchmark_data(baseline_path)
        if not baseline_data:
            print("Warning: Failed to load baseline benchmark data")
            sys.exit(0)
        
        baseline_metrics = checker.extract_performance_metrics(baseline_data)
    else:
        print("No baseline provided - skipping regression analysis")
        sys.exit(0)
    
    # Analyze regressions
    regressions = checker.analyze_regressions(baseline_metrics, current_metrics)
    
    # Generate report
    report = checker.generate_report(regressions, str(args.baseline), str(args.current))
    
    # Output results
    if args.verbose:
        print(f"Analyzed {len(current_metrics)} functions")
        print(f"Found {len(regressions)} performance regressions")
        
        if regressions:
            print("\nRegression Details:")
            for regression in regressions:
                print(f"  {regression.function_name}: {regression.regression_percent:.1%} slower "
                      f"({regression.current_ops_per_sec:.1f} vs {regression.baseline_ops_per_sec:.1f} ops/sec) "
                      f"[{regression.severity.upper()}]")
    
    # Save report if output path provided
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        if args.verbose:
            print(f"\nRegression report saved to: {output_path}")
    
    # Print summary
    summary = report['summary']
    print(f"\nRegression Analysis Summary:")
    print(f"  Total regressions: {summary['total_regressions']}")
    print(f"  Critical: {summary['critical_regressions']}")
    print(f"  High: {summary['high_regressions']}")
    print(f"  Medium: {summary['medium_regressions']}")
    print(f"  Low: {summary['low_regressions']}")
    
    # Exit with appropriate code
    if args.fail_on_regression and summary['has_blocking_regressions']:
        print(f"\nFAILURE: Blocking performance regressions detected!")
        sys.exit(1)
    elif summary['total_regressions'] > 0:
        print(f"\nWARNING: {summary['total_regressions']} performance regressions detected")
        sys.exit(0)
    else:
        print("\nSUCCESS: No performance regressions detected")
        sys.exit(0)


if __name__ == '__main__':
    main()