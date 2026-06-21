"""
Preprocessing Layer - Data Cleaning, Outlier Handling, Normalization
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.impute import SimpleImputer, KNNImputer
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class PreprocessingLayer:
    """Complete data preprocessing pipeline"""

    def __init__(self, config: Dict):
        self.config = config
        self.scaler = None
        self.imputer = None
        self.outlier_params = {}

    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'advanced') -> pd.DataFrame:
        """Handle missing values with multiple strategies"""

        df_clean = df.copy()

        # Separate numeric and categorical
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=['object']).columns

        if strategy == 'advanced':
            # KNN imputation for numeric
            self.imputer = KNNImputer(n_neighbors=5)
            df_clean[numeric_cols] = self.imputer.fit_transform(df_clean[numeric_cols])

            # Mode imputation for categorical
            for col in categorical_cols:
                df_clean[col].fillna(df_clean[col].mode()[0] if len(df_clean[col].mode()) > 0 else 'unknown', inplace=True)

        elif strategy == 'interpolate':
            # Time series interpolation
            for col in numeric_cols:
                if 'timestamp' in df.columns:
                    df_clean[col] = df_clean.set_index('timestamp')[col].interpolate(method='time').values
                else:
                    df_clean[col] = df_clean[col].interpolate(method='linear')

        else:
            # Simple imputation
            num_imputer = SimpleImputer(strategy='median')
            df_clean[numeric_cols] = num_imputer.fit_transform(df_clean[numeric_cols])

            cat_imputer = SimpleImputer(strategy='constant', fill_value='missing')
            df_clean[categorical_cols] = cat_imputer.fit_transform(df_clean[categorical_cols])

        logger.info(f"✅ Handled missing values. Missing ratio: {(df.isnull().sum().sum()/df.size):.2%}")
        return df_clean

    def detect_outliers(self, df: pd.DataFrame, method: str = 'isolation_forest') -> pd.DataFrame:
        """Detect and handle outliers"""

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outlier_flags = pd.DataFrame(index=df.index)

        if method == 'iqr':
            for col in numeric_cols:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR

                outlier_flags[col] = (df[col] < lower_bound) | (df[col] > upper_bound)

                # Store bounds for capping
                self.outlier_params[col] = {'lower': lower_bound, 'upper': upper_bound}

        elif method == 'zscore':
            from scipy import stats
            for col in numeric_cols:
                z_scores = np.abs(stats.zscore(df[col].dropna()))
                threshold = 3
                outlier_flags[col] = z_scores > threshold

        elif method == 'isolation_forest':
            from sklearn.ensemble import IsolationForest
            iso_forest = IsolationForest(contamination=0.1, random_state=42)
            outlier_flags['isolation_forest'] = iso_forest.fit_predict(df[numeric_cols].fillna(0)) == -1

        # Mark rows as outliers if any feature is outlier
        df['is_outlier'] = outlier_flags.any(axis=1)
        outlier_count = df['is_outlier'].sum()

        logger.info(f"✅ Detected {outlier_count} outlier rows ({outlier_count/len(df)*100:.2f}%)")
        return df

    def handle_outliers(self, df: pd.DataFrame, method: str = 'cap') -> pd.DataFrame:
        """Handle outliers by capping or removing"""

        df_clean = df.copy()

        if method == 'cap':
            # Cap outliers to bounds
            for col, params in self.outlier_params.items():
                if col in df_clean.columns:
                    df_clean[col] = df_clean[col].clip(
                        lower=params['lower'],
                        upper=params['upper']
                    )
            logger.info("✅ Capped outliers")

        elif method == 'remove':
            # Remove rows with outliers
            df_clean = df_clean[~df_clean['is_outlier']]
            logger.info(f"✅ Removed {df['is_outlier'].sum()} outlier rows")

        return df_clean

    def normalize_data(self, df: pd.DataFrame, method: str = 'standard') -> pd.DataFrame:
        """Normalize/scale numerical features"""

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if method == 'standard':
            self.scaler = StandardScaler()
        elif method == 'minmax':
            self.scaler = MinMaxScaler()
        elif method == 'robust':
            self.scaler = RobustScaler()
        else:
            self.scaler = StandardScaler()

        df[numeric_cols] = self.scaler.fit_transform(df[numeric_cols].fillna(0))
        logger.info(f"✅ Normalized {len(numeric_cols)} features using {method} scaling")

        return df

    def encode_categorical(self, df: pd.DataFrame, method: str = 'target') -> pd.DataFrame:
        """Encode categorical variables"""

        categorical_cols = df.select_dtypes(include=['object']).columns
        df_encoded = df.copy()

        for col in categorical_cols:
            if method == 'onehot':
                # One-hot encoding for low cardinality
                if df[col].nunique() < 20:
                    dummies = pd.get_dummies(df[col], prefix=col)
                    df_encoded = pd.concat([df_encoded, dummies], axis=1)
                    df_encoded.drop(columns=[col], inplace=True)

            elif method == 'label':
                # Label encoding
                from sklearn.preprocessing import LabelEncoder
                le = LabelEncoder()
                df_encoded[f'{col}_encoded'] = le.fit_transform(df[col].astype(str))
                df_encoded.drop(columns=[col], inplace=True)

            elif method == 'target':
                # Target encoding
                if 'units_sold' in df.columns:
                    target_mean = df.groupby(col)['units_sold'].mean()
                    df_encoded[f'{col}_target_encoded'] = df[col].map(target_mean)
                    df_encoded.drop(columns=[col], inplace=True)

        logger.info(f"✅ Encoded {len(categorical_cols)} categorical features")
        return df_encoded

    def feature_selection(self, df: pd.DataFrame, target_col: str = 'units_sold',
                          k: int = 50) -> pd.DataFrame:
        """Select top k features based on importance"""

        from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression

        # Separate features and target
        X = df.drop(columns=[target_col])
        y = df[target_col]

        # Select features
        selector = SelectKBest(score_func=mutual_info_regression, k=min(k, len(X.columns)))
        X_selected = selector.fit_transform(X.fillna(0), y)

        # Get selected feature names
        selected_features = X.columns[selector.get_support()].tolist()
        selected_features.append(target_col)

        df_selected = df[selected_features]
        logger.info(f"✅ Selected {len(selected_features)} features from {len(df.columns)}")

        return df_selected

    def create_time_series_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create time series specific features"""

        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Basic time features
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['day_of_month'] = df['timestamp'].dt.day
            df['week_of_year'] = df['timestamp'].dt.isocalendar().week
            df['month'] = df['timestamp'].dt.month
            df['quarter'] = df['timestamp'].dt.quarter
            df['year'] = df['timestamp'].dt.year
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

            # Cyclical encoding
            df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
            df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

            # Lag features
            if 'units_sold' in df.columns:
                for lag in [1, 7, 14, 28]:
                    df[f'units_sold_lag_{lag}'] = df['units_sold'].shift(lag)

            # Rolling statistics
            for window in [7, 14, 30]:
                df[f'units_sold_rolling_mean_{window}'] = df['units_sold'].rolling(window).mean()
                df[f'units_sold_rolling_std_{window}'] = df['units_sold'].rolling(window).std()

        return df

    def run_preprocessing_pipeline(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        """Execute complete preprocessing pipeline"""

        logger.info("Starting preprocessing pipeline...")

        # Step 1: Handle missing values
        df = self.handle_missing_values(df)

        # Step 2: Detect and handle outliers
        df = self.detect_outliers(df)
        df = self.handle_outliers(df, method='cap')

        # Step 3: Create time series features
        df = self.create_time_series_features(df)

        # Step 4: Encode categorical variables
        df = self.encode_categorical(df, method='target')

        # Step 5: Normalize numerical features
        df = self.normalize_data(df)

        # Step 6: Feature selection (only for training)
        if is_training and 'units_sold' in df.columns:
            df = self.feature_selection(df)

        # Step 7: Remove rows with NaN (from lag creation)
        df = df.dropna()

        logger.info(f"✅ Preprocessing complete. Final shape: {df.shape}")
        return df