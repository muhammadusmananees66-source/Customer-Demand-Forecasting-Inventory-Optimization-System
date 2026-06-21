"""
Validation & EDA Layer - Data Quality, Schema Validation, Statistical Analysis
"""

import pandas as pd
import numpy as np
from great_expectations.dataset import PandasDataset
from pandera import DataFrameSchema, Column, Check, Index
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class DataValidationLayer:
    """Complete data validation and quality checks"""

    def __init__(self):
        self.schema = None
        self.expectations = []
        self.quality_report = {}

    def define_schema(self):
        """Define schema for demand data"""

        self.schema = DataFrameSchema({
            'product_id': Column(str, Check.str_length(1, 50), nullable=False),
            'store_id': Column(str, Check.str_length(1, 20), nullable=False),
            'timestamp': Column(pd.DatetimeTZDtype, nullable=False),
            'units_sold': Column(int, [
                Check.greater_than_or_equal_to(0),
                Check.less_than_or_equal_to(10000)
            ], nullable=False),
            'price': Column(float, [
                Check.greater_than_or_equal_to(0),
                Check.less_than_or_equal_to(10000)
            ], nullable=False),
            'discount': Column(float, [
                Check.greater_than_or_equal_to(0),
                Check.less_than_or_equal_to(1)
            ], nullable=True),
            'inventory_level': Column(int, Check.greater_than_or_equal_to(0), nullable=False),
            'competitor_price': Column(float, Check.greater_than_or_equal_to(0), nullable=True),
            'weather_temp': Column(float, Check.in_range(-50, 60), nullable=True),
            'promotion_flag': Column(bool, nullable=True),
            'category': Column(str, nullable=True)
        })

    def validate_schema(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate dataframe against schema"""
        errors = []

        try:
            self.schema.validate(df, lazy=True)
        except Exception as e:
            errors.append(str(e))
            return False, errors

        # Additional business rules
        if 'units_sold' in df.columns and 'inventory_level' in df.columns:
            if (df['units_sold'] > df['inventory_level']).any():
                errors.append("Units sold exceeds inventory level")

        return len(errors) == 0, errors

    def check_data_quality(self, df: pd.DataFrame) -> Dict:
        """Comprehensive data quality checks"""

        quality_metrics = {
            'completeness': {},
            'uniqueness': {},
            'consistency': {},
            'accuracy': {},
            'timeliness': {}
        }

        # Completeness
        for col in df.columns:
            completeness = 1 - df[col].isnull().sum() / len(df)
            quality_metrics['completeness'][col] = completeness

        # Uniqueness
        for col in df.select_dtypes(include=['object']).columns:
            uniqueness = df[col].nunique() / len(df)
            quality_metrics['uniqueness'][col] = uniqueness

        # Consistency checks
        if 'units_sold' in df.columns and 'price' in df.columns:
            revenue_consistency = (df['units_sold'] * df['price']).corr(df.get('revenue', pd.Series()))
            quality_metrics['consistency']['revenue_correlation'] = revenue_consistency

        # Accuracy - check for outliers
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            outliers = ((df[col] < (q1 - 1.5 * iqr)) | (df[col] > (q3 + 1.5 * iqr))).sum()
            quality_metrics['accuracy'][f'{col}_outlier_ratio'] = outliers / len(df)

        # Overall quality score
        quality_metrics['overall_score'] = np.mean([
            np.mean(list(quality_metrics['completeness'].values())),
            1 - np.mean(list(quality_metrics['accuracy'].values()))
        ])

        return quality_metrics

    def exploratory_analysis(self, df: pd.DataFrame) -> Dict:
        """Comprehensive EDA"""

        eda_report = {
            'basic_stats': {},
            'distributions': {},
            'correlations': {},
            'time_series': {},
            'seasonality': {}
        }

        # Basic statistics
        eda_report['basic_stats']['shape'] = df.shape
        eda_report['basic_stats']['dtypes'] = df.dtypes.to_dict()
        eda_report['basic_stats']['missing'] = df.isnull().sum().to_dict()

        # Numerical distributions
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            eda_report['distributions'][col] = {
                'mean': df[col].mean(),
                'median': df[col].median(),
                'std': df[col].std(),
                'skewness': df[col].skew(),
                'kurtosis': df[col].kurtosis()
            }

        # Correlation analysis
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            eda_report['correlations']['matrix'] = corr_matrix.to_dict()

            # Find top correlations with target
            if 'units_sold' in corr_matrix.columns:
                top_corr = corr_matrix['units_sold'].abs().sort_values(ascending=False)
                eda_report['correlations']['top_with_target'] = top_corr.head(10).to_dict()

        # Time series analysis
        if 'timestamp' in df.columns:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            daily_sales = df.groupby('date')['units_sold'].sum()

            # Trend analysis
            from scipy import signal
            trend = signal.savgol_filter(daily_sales, window_length=7, polyorder=2)
            eda_report['time_series']['trend'] = trend.tolist()

            # Seasonality detection
            from statsmodels.tsa.seasonal import seasonal_decompose
            if len(daily_sales) > 30:
                decomposition = seasonal_decompose(daily_sales, model='additive', period=7)
                eda_report['seasonality']['weekly'] = decomposition.seasonal.tolist()

        return eda_report

    def statistical_tests(self, df: pd.DataFrame) -> Dict:
        """Run statistical tests for data quality"""

        test_results = {}

        # Normality test for numerical columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols[:5]:  # Limit to first 5 for performance
            statistic, p_value = stats.normaltest(df[col].dropna())
            test_results[f'{col}_normality'] = {
                'statistic': statistic,
                'p_value': p_value,
                'is_normal': p_value > 0.05
            }

        # Stationarity test for time series
        if 'units_sold' in df.columns and len(df) > 30:
            from statsmodels.tsa.stattools import adfuller
            result = adfuller(df['units_sold'].dropna())
            test_results['units_sold_stationarity'] = {
                'adf_statistic': result[0],
                'p_value': result[1],
                'is_stationary': result[1] < 0.05
            }

        # ANOVA for categorical features
        categorical_cols = df.select_dtypes(include=['object']).columns
        for cat_col in categorical_cols[:3]:  # Limit to first 3
            if 'units_sold' in df.columns and df[cat_col].nunique() > 1:
                groups = [df[df[cat_col] == value]['units_sold'].dropna()
                         for value in df[cat_col].unique()[:5]]
                if all(len(g) > 0 for g in groups):
                    f_stat, p_value = stats.f_oneway(*groups)
                    test_results[f'{cat_col}_ANOVA'] = {
                        'f_statistic': f_stat,
                        'p_value': p_value,
                        'significant': p_value < 0.05
                    }

        return test_results

    def generate_validation_report(self, df: pd.DataFrame) -> Dict:
        """Generate complete validation report"""

        report = {
            'timestamp': datetime.now().isoformat(),
            'schema_valid': None,
            'quality_metrics': {},
            'eda_report': {},
            'statistical_tests': {},
            'recommendations': []
        }

        # Run all validations
        schema_valid, schema_errors = self.validate_schema(df)
        report['schema_valid'] = schema_valid
        report['schema_errors'] = schema_errors

        report['quality_metrics'] = self.check_data_quality(df)
        report['eda_report'] = self.exploratory_analysis(df)
        report['statistical_tests'] = self.statistical_tests(df)

        # Generate recommendations
        if report['quality_metrics']['overall_score'] < 0.8:
            report['recommendations'].append("Data quality score below threshold. Consider data cleaning.")

        if report['statistical_tests'].get('units_sold_stationarity', {}).get('is_stationary') == False:
            report['recommendations'].append("Time series is non-stationary. Apply differencing.")

        # Save report
        self._save_report(report)

        return report

    def _save_report(self, report: Dict):
        """Save validation report"""
        import json
        filename = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(f"reports/validation/{filename}", 'w') as f:
            json.dump(report, f, indent=2, default=str)