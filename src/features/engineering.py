# # # """
# # # Feature Engineering - 50+ features
# # # """


# # # from typing import Any

# # # import numpy as np
# # # import pandas as pd
# # # import structlog
# # # from sklearn.preprocessing import OneHotEncoder, StandardScaler

# # # logger = structlog.get_logger()


# # # class FeatureEngineer:
# # #     def __init__(self, config: dict[str, Any]):
# # #         self.config = config
# # #         self.time_features = config.get("time_features", True)
# # #         self.lag_features = config.get("lag_features", [1, 7, 14, 30])
# # #         self.rolling_windows = config.get("rolling_windows", [7, 14, 30, 90])
# # #         self.group_by = config.get("group_by", ["product_id"])
# # #         self.target = config.get("target", "quantity")
# # #         self.date_col = config.get("date_col", "date")
# # #         self.scaler = None
# # #         self.encoder = None

# # #     def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         df = df.copy()
# # #         if self.date_col in df.columns:
# # #             df = df.sort_values(self.date_col)

# # #         if self.time_features:
# # #             df = self._add_time_features(df)

# # #         df = self._add_lag_features(df)
# # #         df = self._add_rolling_features(df)
# # #         df = self._add_aggregation_features(df)
# # #         df = self._add_interaction_features(df)
# # #         df = self._encode_categorical(df)
# # #         df = self._scale_features(df)
# # #         df = self._add_seasonal_features(df)

# # #         return df

# # #     def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         if self.date_col not in df.columns:
# # #             return df
# # #         dt = pd.to_datetime(df[self.date_col])
# # #         df['day_of_week'] = dt.dt.dayofweek
# # #         df['day_of_month'] = dt.dt.day
# # #         df['day_of_year'] = dt.dt.dayofyear
# # #         df['week_of_year'] = dt.dt.isocalendar().week
# # #         df['month'] = dt.dt.month
# # #         df['quarter'] = dt.dt.quarter
# # #         df['year'] = dt.dt.year
# # #         df['is_weekend'] = (dt.dt.dayofweek >= 5).astype(int)
# # #         df['is_month_start'] = dt.dt.is_month_start.astype(int)
# # #         df['is_month_end'] = dt.dt.is_month_end.astype(int)
# # #         df['is_quarter_start'] = dt.dt.is_quarter_start.astype(int)
# # #         df['is_quarter_end'] = dt.dt.is_quarter_end.astype(int)
# # #         df['days_until_holiday'] = self._calculate_holiday_distance(dt)
# # #         df['weeks_until_holiday'] = df['days_until_holiday'] // 7
# # #         return df

# # #     def _calculate_holiday_distance(self, dt: pd.Series) -> pd.Series:
# # #         holidays = pd.to_datetime(["2024-01-01", "2024-12-25", "2024-11-28", "2024-07-04"])
# # #         def distance_to_holiday(date):
# # #             min_dist = min(abs(date - h).days for h in holidays)
# # #             return min_dist
# # #         return dt.apply(distance_to_holiday)

# # #     def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         for lag in self.lag_features:
# # #             df[f'{self.target}_lag_{lag}'] = df.groupby(self.group_by)[self.target].shift(lag)
# # #         if 'price' in df.columns:
# # #             for lag in self.lag_features[:3]:
# # #                 df[f'price_lag_{lag}'] = df.groupby(self.group_by)['price'].shift(lag)
# # #         return df

# # #     def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         for window in self.rolling_windows:
# # #             df[f'{self.target}_roll_mean_{window}'] = df.groupby(self.group_by)[self.target].rolling(window).mean().reset_index(level=0, drop=True)
# # #             df[f'{self.target}_roll_std_{window}'] = df.groupby(self.group_by)[self.target].rolling(window).std().reset_index(level=0, drop=True)
# # #             df[f'{self.target}_roll_min_{window}'] = df.groupby(self.group_by)[self.target].rolling(window).min().reset_index(level=0, drop=True)
# # #             df[f'{self.target}_roll_max_{window}'] = df.groupby(self.group_by)[self.target].rolling(window).max().reset_index(level=0, drop=True)
# # #             if 'price' in df.columns:
# # #                 df[f'price_roll_mean_{window}'] = df.groupby(self.group_by)['price'].rolling(window).mean().reset_index(level=0, drop=True)
# # #         return df

# # #     def _add_aggregation_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         agg_dict = {self.target: ['mean', 'std', 'min', 'max', 'sum', 'count'], 'price': ['mean', 'std', 'min', 'max']}
# # #         if 'store_id' in df.columns:
# # #             agg_dict['store_id'] = ['nunique']
# # #         aggregations = df.groupby(self.group_by).agg(agg_dict)
# # #         aggregations.columns = ['_'.join(col).strip() for col in aggregations.columns.values]
# # #         aggregations = aggregations.reset_index()
# # #         df = df.merge(aggregations, on=self.group_by, how='left')
# # #         return df

# # #     def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         if self.target in df.columns and 'price' in df.columns:
# # #             df['revenue'] = df[self.target] * df['price']
# # #             df['log_quantity'] = np.log1p(df[self.target])
# # #             df['log_price'] = np.log1p(df['price'])
# # #             df['log_revenue'] = np.log1p(df['revenue'])
# # #         if 'quantity_lag_1' in df.columns:
# # #             df['quantity_change'] = df[self.target] - df['quantity_lag_1']
# # #             df['quantity_change_pct'] = (df['quantity_change'] / (df['quantity_lag_1'] + 1)) * 100
# # #         return df

# # #     def _add_seasonal_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         if self.date_col not in df.columns:
# # #             return df
# # #         dt = pd.to_datetime(df[self.date_col])
# # #         df['month_sin'] = np.sin(2 * np.pi * dt.dt.month / 12)
# # #         df['month_cos'] = np.cos(2 * np.pi * dt.dt.month / 12)
# # #         df['day_of_week_sin'] = np.sin(2 * np.pi * dt.dt.dayofweek / 7)
# # #         df['day_of_week_cos'] = np.cos(2 * np.pi * dt.dt.dayofweek / 7)
# # #         return df

# # #     def _encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         categorical_cols = [c for c in df.select_dtypes(include=['object', 'category']).columns if c not in self.group_by]
# # #         if not categorical_cols:
# # #             return df
# # #         if self.encoder is None:
# # #             self.encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
# # #             encoded = self.encoder.fit_transform(df[categorical_cols])
# # #             feature_names = self.encoder.get_feature_names_out(categorical_cols)
# # #         else:
# # #             encoded = self.encoder.transform(df[categorical_cols])
# # #             feature_names = self.encoder.get_feature_names_out(categorical_cols)
# # #         encoded_df = pd.DataFrame(encoded, columns=feature_names, index=df.index)
# # #         df = pd.concat([df, encoded_df], axis=1)
# # #         df = df.drop(columns=categorical_cols)
# # #         return df

# # #     def _scale_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         numerical_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in self.group_by]
# # #         if not numerical_cols:
# # #             return df
# # #         if self.scaler is None:
# # #             self.scaler = StandardScaler()
# # #             df[numerical_cols] = self.scaler.fit_transform(df[numerical_cols])
# # #         else:
# # #             df[numerical_cols] = self.scaler.transform(df[numerical_cols])
# # #         return df


# # # class FeatureSelector:
# # #     def __init__(self, config: dict[str, Any]):
# # #         self.config = config
# # #         self.method = config.get("method", "importance")
# # #         self.num_features = config.get("num_features", 50)

# # #     def select_features(self, x: pd.DataFrame, y: pd.Series) -> list[str]:
# # #         from sklearn.ensemble import RandomForestRegressor
# # #         from sklearn.feature_selection import RFE

# # #         if self.method == "importance":
# # #             model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
# # #             model.fit(x, y)
# # #             importances = model.feature_importances_
# # #             indices = np.argsort(importances)[::-1]
# # #             return x.columns[indices[:self.num_features]].tolist()
# # #         elif self.method == "rfe":
# # #             model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
# # #             rfe = RFE(model, n_features_to_select=self.num_features)
# # #             rfe.fit(x, y)
# # #             return x.columns[rfe.support_].tolist()
# # #         else:
# # #             correlations = x.corrwith(y).abs().sort_values(ascending=False)
# # #             return correlations.head(self.num_features).index.tolist()


# # # """
# # # Feature Engineering - 50+ features
# # # """

# # # from typing import Any, cast

# # # import numpy as np
# # # import pandas as pd
# # # import structlog
# # # from sklearn.preprocessing import OneHotEncoder, StandardScaler

# # # logger = structlog.get_logger()


# # # class FeatureEngineer:
# # #     def __init__(self, config: dict[str, Any]):
# # #         self.config = config
# # #         self.time_features = config.get("time_features", True)
# # #         self.lag_features = config.get("lag_features", [1, 7, 14, 30])
# # #         self.rolling_windows = config.get("rolling_windows", [7, 14, 30, 90])
# # #         self.group_by = config.get("group_by", ["product_id"])
# # #         self.target = config.get("target", "quantity")
# # #         self.date_col = config.get("date_col", "date")
# # #         self.scaler: StandardScaler | None = None
# # #         self.encoder: OneHotEncoder | None = None

# # #     def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         """Create all features for the dataset."""
# # #         df = df.copy()
# # #         if self.date_col in df.columns:
# # #             df = df.sort_values(self.date_col)

# # #         if self.time_features:
# # #             df = self._add_time_features(df)

# # #         df = self._add_lag_features(df)
# # #         df = self._add_rolling_features(df)
# # #         df = self._add_aggregation_features(df)
# # #         df = self._add_interaction_features(df)
# # #         df = self._encode_categorical(df)
# # #         df = self._scale_features(df)
# # #         df = self._add_seasonal_features(df)

# # #         return df

# # #     def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         """Add time-based features from date column."""
# # #         if self.date_col not in df.columns:
# # #             return df
# # #         dt = pd.to_datetime(df[self.date_col])
# # #         df['day_of_week'] = dt.dt.dayofweek
# # #         df['day_of_month'] = dt.dt.day
# # #         df['day_of_year'] = dt.dt.dayofyear
# # #         df['week_of_year'] = dt.dt.isocalendar().week
# # #         df['month'] = dt.dt.month
# # #         df['quarter'] = dt.dt.quarter
# # #         df['year'] = dt.dt.year
# # #         df['is_weekend'] = (dt.dt.dayofweek >= 5).astype(int)
# # #         df['is_month_start'] = dt.dt.is_month_start.astype(int)
# # #         df['is_month_end'] = dt.dt.is_month_end.astype(int)
# # #         df['is_quarter_start'] = dt.dt.is_quarter_start.astype(int)
# # #         df['is_quarter_end'] = dt.dt.is_quarter_end.astype(int)
# # #         df['days_until_holiday'] = self._calculate_holiday_distance(dt)
# # #         df['weeks_until_holiday'] = df['days_until_holiday'] // 7
# # #         return df

# # #     def _calculate_holiday_distance(self, dt: pd.Series) -> pd.Series:
# # #         """Calculate distance to nearest holiday."""
# # #         holidays = pd.to_datetime(["2024-01-01", "2024-12-25", "2024-11-28", "2024-07-04"])

# # #         def distance_to_holiday(date: pd.Timestamp) -> int:
# # #             min_dist = min(abs(date - h).days for h in holidays)
# # #             return min_dist

# # #         return dt.apply(distance_to_holiday)

# # #     def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         """Add lag features for the target and price."""
# # #         for lag in self.lag_features:
# # #             df[f'{self.target}_lag_{lag}'] = df.groupby(self.group_by)[self.target].shift(lag)
# # #         if 'price' in df.columns:
# # #             for lag in self.lag_features[:3]:
# # #                 df[f'price_lag_{lag}'] = df.groupby(self.group_by)['price'].shift(lag)
# # #         return df

# # #     def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         """Add rolling statistics features."""
# # #         for window in self.rolling_windows:
# # #             df[f'{self.target}_roll_mean_{window}'] = (
# # #                 df.groupby(self.group_by)[self.target]
# # #                 .rolling(window)
# # #                 .mean()
# # #                 .reset_index(level=0, drop=True)
# # #             )
# # #             df[f'{self.target}_roll_std_{window}'] = (
# # #                 df.groupby(self.group_by)[self.target]
# # #                 .rolling(window)
# # #                 .std()
# # #                 .reset_index(level=0, drop=True)
# # #             )
# # #             df[f'{self.target}_roll_min_{window}'] = (
# # #                 df.groupby(self.group_by)[self.target]
# # #                 .rolling(window)
# # #                 .min()
# # #                 .reset_index(level=0, drop=True)
# # #             )
# # #             df[f'{self.target}_roll_max_{window}'] = (
# # #                 df.groupby(self.group_by)[self.target]
# # #                 .rolling(window)
# # #                 .max()
# # #                 .reset_index(level=0, drop=True)
# # #             )
# # #             if 'price' in df.columns:
# # #                 df[f'price_roll_mean_{window}'] = (
# # #                     df.groupby(self.group_by)['price']
# # #                     .rolling(window)
# # #                     .mean()
# # #                     .reset_index(level=0, drop=True)
# # #                 )
# # #         return df

# # #     def _add_aggregation_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         """Add aggregation features grouped by product/other columns."""
# # #         agg_dict = {
# # #             self.target: ['mean', 'std', 'min', 'max', 'sum', 'count'],
# # #             'price': ['mean', 'std', 'min', 'max']
# # #         }
# # #         if 'store_id' in df.columns:
# # #             agg_dict['store_id'] = ['nunique']
# # #         aggregations = df.groupby(self.group_by).agg(agg_dict)
# # #         aggregations.columns = ['_'.join(col).strip() for col in aggregations.columns.values]
# # #         aggregations = aggregations.reset_index()
# # #         df = df.merge(aggregations, on=self.group_by, how='left')
# # #         return df

# # #     def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         """Add interaction features between existing features."""
# # #         if self.target in df.columns and 'price' in df.columns:
# # #             df['revenue'] = df[self.target] * df['price']
# # #             df['log_quantity'] = np.log1p(df[self.target])
# # #             df['log_price'] = np.log1p(df['price'])
# # #             df['log_revenue'] = np.log1p(df['revenue'])
# # #         if 'quantity_lag_1' in df.columns:
# # #             df['quantity_change'] = df[self.target] - df['quantity_lag_1']
# # #             df['quantity_change_pct'] = (df['quantity_change'] / (df['quantity_lag_1'] + 1)) * 100
# # #         return df

# # #     def _add_seasonal_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         """Add seasonal features using sine/cosine transformations."""
# # #         if self.date_col not in df.columns:
# # #             return df
# # #         dt = pd.to_datetime(df[self.date_col])
# # #         df['month_sin'] = np.sin(2 * np.pi * dt.dt.month / 12)
# # #         df['month_cos'] = np.cos(2 * np.pi * dt.dt.month / 12)
# # #         df['day_of_week_sin'] = np.sin(2 * np.pi * dt.dt.dayofweek / 7)
# # #         df['day_of_week_cos'] = np.cos(2 * np.pi * dt.dt.dayofweek / 7)
# # #         return df

# # #     def _encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         """Encode categorical variables using one-hot encoding."""
# # #         categorical_cols = [
# # #             c for c in df.select_dtypes(include=['object', 'category']).columns
# # #             if c not in self.group_by
# # #         ]
# # #         if not categorical_cols:
# # #             return df

# # #         if self.encoder is None:
# # #             self.encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
# # #             encoded = self.encoder.fit_transform(df[categorical_cols])
# # #             feature_names = cast(list[str], self.encoder.get_feature_names_out(categorical_cols))
# # #         else:
# # #             encoded = self.encoder.transform(df[categorical_cols])
# # #             feature_names = cast(list[str], self.encoder.get_feature_names_out(categorical_cols))

# # #         encoded_df = pd.DataFrame(encoded, columns=feature_names, index=df.index)
# # #         df = pd.concat([df, encoded_df], axis=1)
# # #         df = df.drop(columns=categorical_cols)
# # #         return df

# # #     def _scale_features(self, df: pd.DataFrame) -> pd.DataFrame:
# # #         """Scale numerical features using StandardScaler."""
# # #         numerical_cols = [
# # #             c for c in df.select_dtypes(include=[np.number]).columns
# # #             if c not in self.group_by
# # #         ]
# # #         if not numerical_cols:
# # #             return df

# # #         if self.scaler is None:
# # #             self.scaler = StandardScaler()
# # #             df[numerical_cols] = self.scaler.fit_transform(df[numerical_cols])
# # #         else:
# # #             df[numerical_cols] = self.scaler.transform(df[numerical_cols])
# # #         return df


# # # class FeatureSelector:
# # #     def __init__(self, config: dict[str, Any]):
# # #         self.config = config
# # #         self.method = config.get("method", "importance")
# # #         self.num_features = config.get("num_features", 50)

# # #     def select_features(self, x: pd.DataFrame, y: pd.Series) -> list[str]:
# # #         """
# # #         Select the most important features using various methods.

# # #         Args:
# # #             x: Feature matrix
# # #             y: Target variable

# # #         Returns:
# # #             List of selected feature names
# # #         """
# # #         from sklearn.ensemble import RandomForestRegressor
# # #         from sklearn.feature_selection import RFE

# # #         if self.method == "importance":
# # #             model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
# # #             model.fit(x, y)
# # #             importances = model.feature_importances_
# # #             indices = np.argsort(importances)[::-1]
# # #             selected = x.columns[indices[:self.num_features]].tolist()
# # #             return cast(list[str], selected)
# # #         elif self.method == "rfe":
# # #             model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
# # #             rfe = RFE(model, n_features_to_select=self.num_features)
# # #             rfe.fit(x, y)
# # #             selected = x.columns[rfe.support_].tolist()
# # #             return cast(list[str], selected)
# # #         else:
# # #             correlations = x.corrwith(y).abs().sort_values(ascending=False)
# # #             selected = correlations.head(self.num_features).index.tolist()
# # #             return cast(list[str], selected)


# """
# Feature Engineering - 50+ features
# """

# from typing import Any, cast

# import numpy as np
# import pandas as pd
# import structlog
# from sklearn.preprocessing import OneHotEncoder, StandardScaler

# logger = structlog.get_logger()


# class FeatureEngineer:
#     def __init__(self, config: dict[str, Any]):
#         self.config = config
#         self.time_features = config.get("time_features", True)
#         self.lag_features = config.get("lag_features", [1, 7, 14, 30])
#         self.rolling_windows = config.get("rolling_windows", [7, 14, 30, 90])
#         self.group_by = config.get("group_by", ["product_id"])
#         self.target = config.get("target", "quantity")
#         self.date_col = config.get("date_col", "date")
#         self.scaler: StandardScaler | None = None
#         self.encoder: OneHotEncoder | None = None

#     def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Create all features for the dataset."""
#         df = df.copy()
#         if self.date_col in df.columns:
#             df = df.sort_values(self.date_col)

#         if self.time_features:
#             df = self._add_time_features(df)

#         df = self._add_lag_features(df)
#         df = self._add_rolling_features(df)
#         df = self._add_aggregation_features(df)
#         df = self._add_interaction_features(df)
#         df = self._encode_categorical(df)
#         df = self._scale_features(df)
#         df = self._add_seasonal_features(df)

#         return df

#     def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Add time-based features from date column."""
#         if self.date_col not in df.columns:
#             return df
#         dt = pd.to_datetime(df[self.date_col])
#         df["day_of_week"] = dt.dt.dayofweek
#         df["day_of_month"] = dt.dt.day
#         df["day_of_year"] = dt.dt.dayofyear
#         df["week_of_year"] = dt.dt.isocalendar().week
#         df["month"] = dt.dt.month
#         df["quarter"] = dt.dt.quarter
#         df["year"] = dt.dt.year
#         df["is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)
#         df["is_month_start"] = dt.dt.is_month_start.astype(int)
#         df["is_month_end"] = dt.dt.is_month_end.astype(int)
#         df["is_quarter_start"] = dt.dt.is_quarter_start.astype(int)
#         df["is_quarter_end"] = dt.dt.is_quarter_end.astype(int)
#         df["days_until_holiday"] = self._calculate_holiday_distance(dt)
#         df["weeks_until_holiday"] = df["days_until_holiday"] // 7
#         return df

#     def _calculate_holiday_distance(self, dt: pd.Series) -> pd.Series:
#         """Calculate distance to nearest holiday."""
#         holidays = pd.to_datetime(["2024-01-01", "2024-12-25", "2024-11-28", "2024-07-04"])

#         def distance_to_holiday(date: pd.Timestamp) -> int:
#             min_dist = min(abs(date - h).days for h in holidays)
#             return int(min_dist)  # Cast to int to ensure type safety

#         return dt.apply(distance_to_holiday)

#     def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Add lag features for the target and price."""
#         for lag in self.lag_features:
#             df[f"{self.target}_lag_{lag}"] = df.groupby(self.group_by)[self.target].shift(lag)
#         if "price" in df.columns:
#             for lag in self.lag_features[:3]:
#                 df[f"price_lag_{lag}"] = df.groupby(self.group_by)["price"].shift(lag)
#         return df

#     def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Add rolling statistics features."""
#         for window in self.rolling_windows:
#             df[f"{self.target}_roll_mean_{window}"] = (
#                 df.groupby(self.group_by)[self.target]
#                 .rolling(window)
#                 .mean()
#                 .reset_index(level=0, drop=True)
#             )
#             df[f"{self.target}_roll_std_{window}"] = (
#                 df.groupby(self.group_by)[self.target]
#                 .rolling(window)
#                 .std()
#                 .reset_index(level=0, drop=True)
#             )
#             df[f"{self.target}_roll_min_{window}"] = (
#                 df.groupby(self.group_by)[self.target]
#                 .rolling(window)
#                 .min()
#                 .reset_index(level=0, drop=True)
#             )
#             df[f"{self.target}_roll_max_{window}"] = (
#                 df.groupby(self.group_by)[self.target]
#                 .rolling(window)
#                 .max()
#                 .reset_index(level=0, drop=True)
#             )
#             if "price" in df.columns:
#                 df[f"price_roll_mean_{window}"] = (
#                     df.groupby(self.group_by)["price"]
#                     .rolling(window)
#                     .mean()
#                     .reset_index(level=0, drop=True)
#                 )
#         return df

#     def _add_aggregation_features(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Add aggregation features grouped by product/other columns."""
#         agg_dict = {
#             self.target: ["mean", "std", "min", "max", "sum", "count"],
#             "price": ["mean", "std", "min", "max"],
#         }
#         if "store_id" in df.columns:
#             agg_dict["store_id"] = ["nunique"]
#         aggregations = df.groupby(self.group_by).agg(agg_dict)
#         aggregations.columns = ["_".join(col).strip() for col in aggregations.columns.values]
#         aggregations = aggregations.reset_index()
#         df = df.merge(aggregations, on=self.group_by, how="left")
#         return df

#     def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Add interaction features between existing features."""
#         if self.target in df.columns and "price" in df.columns:
#             df["revenue"] = df[self.target] * df["price"]
#             df["log_quantity"] = np.log1p(df[self.target])
#             df["log_price"] = np.log1p(df["price"])
#             df["log_revenue"] = np.log1p(df["revenue"])
#         if "quantity_lag_1" in df.columns:
#             df["quantity_change"] = df[self.target] - df["quantity_lag_1"]
#             df["quantity_change_pct"] = (df["quantity_change"] / (df["quantity_lag_1"] + 1)) * 100
#         return df

#     def _add_seasonal_features(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Add seasonal features using sine/cosine transformations."""
#         if self.date_col not in df.columns:
#             return df
#         dt = pd.to_datetime(df[self.date_col])
#         df["month_sin"] = np.sin(2 * np.pi * dt.dt.month / 12)
#         df["month_cos"] = np.cos(2 * np.pi * dt.dt.month / 12)
#         df["day_of_week_sin"] = np.sin(2 * np.pi * dt.dt.dayofweek / 7)
#         df["day_of_week_cos"] = np.cos(2 * np.pi * dt.dt.dayofweek / 7)
#         return df

#     def _encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Encode categorical variables using one-hot encoding."""
#         categorical_cols = [
#             c
#             for c in df.select_dtypes(include=["object", "category"]).columns
#             if c not in self.group_by
#         ]
#         if not categorical_cols:
#             return df

#         if self.encoder is None:
#             self.encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
#             encoded = self.encoder.fit_transform(df[categorical_cols])
#             feature_names = cast(list[str], self.encoder.get_feature_names_out(categorical_cols))
#         else:
#             encoded = self.encoder.transform(df[categorical_cols])
#             feature_names = cast(list[str], self.encoder.get_feature_names_out(categorical_cols))

#         encoded_df = pd.DataFrame(encoded, columns=feature_names, index=df.index)
#         df = pd.concat([df, encoded_df], axis=1)
#         df = df.drop(columns=categorical_cols)
#         return df

#     def _scale_features(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Scale numerical features using StandardScaler."""
#         numerical_cols = [
#             c for c in df.select_dtypes(include=[np.number]).columns if c not in self.group_by
#         ]
#         if not numerical_cols:
#             return df

#         if self.scaler is None:
#             self.scaler = StandardScaler()
#             df[numerical_cols] = self.scaler.fit_transform(df[numerical_cols])
#         else:
#             df[numerical_cols] = self.scaler.transform(df[numerical_cols])
#         return df


# class FeatureSelector:
#     def __init__(self, config: dict[str, Any]):
#         self.config = config
#         self.method = config.get("method", "importance")
#         self.num_features = config.get("num_features", 50)

#     def select_features(self, x: pd.DataFrame, y: pd.Series) -> list[str]:
#         """
#         Select the most important features using various methods.

#         Args:
#             x: Feature matrix
#             y: Target variable

#         Returns:
#             List of selected feature names
#         """
#         from sklearn.ensemble import RandomForestRegressor
#         from sklearn.feature_selection import RFE

#         if self.method == "importance":
#             model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
#             model.fit(x, y)
#             importances = model.feature_importances_
#             indices = np.argsort(importances)[::-1]
#             selected = x.columns[indices[: self.num_features]].tolist()
#             return cast(list[str], selected)
#         elif self.method == "rfe":
#             model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
#             rfe = RFE(model, n_features_to_select=self.num_features)
#             rfe.fit(x, y)
#             selected = x.columns[rfe.support_].tolist()
#             return cast(list[str], selected)
#         else:
#             correlations = x.corrwith(y).abs().sort_values(ascending=False)
#             selected = correlations.head(self.num_features).index.tolist()
#             return cast(list[str], selected)


# # # src/features/engineering.py (complete file with fix)

# # import pandas as pd
# # import numpy as np
# # from sklearn.preprocessing import StandardScaler, OneHotEncoder
# # from typing import Optional, List, Dict, Any
# # import logging

# # logger = logging.getLogger(__name__)


# # class FeatureEngineer:
# #     """Feature engineering class for demand forecasting"""

# #     def __init__(self, config: Dict[str, Any]):
# #         """
# #         Initialize FeatureEngineer with configuration.

# #         Args:
# #             config: Configuration dictionary containing feature engineering parameters
# #         """
# #         self.config = config
# #         self.time_features = config.get('time_features', True)
# #         self.lag_features = config.get('lag_features', [1, 7])
# #         self.rolling_windows = config.get('rolling_windows', [7, 14])
# #         self.group_by = config.get('group_by', ['product_id'])
# #         self.target = config.get('target', 'quantity')
# #         self.date_col = config.get('date_col', 'date')
# #         self.categorical_columns = config.get('categorical_columns', [])
# #         self.scaler = None
# #         self.encoder = None

# #     def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
# #         """
# #         Create all features for demand forecasting.

# #         Args:
# #             df: Input DataFrame

# #         Returns:
# #             DataFrame with engineered features
# #         """
# #         logger.info("Starting feature engineering pipeline")
# #         result = df.copy()

# #         # Ensure date column is datetime
# #         if self.date_col in result.columns:
# #             result[self.date_col] = pd.to_datetime(result[self.date_col])
# #             result = result.sort_values(self.date_col)

# #         # Add time features
# #         if self.time_features:
# #             result = self._add_time_features(result)
# #             logger.debug("Added time features")

# #         # Add lag features
# #         if self.lag_features:
# #             result = self._add_lag_features(result)
# #             logger.debug("Added lag features")

# #         # Add rolling features
# #         if self.rolling_windows:
# #             result = self._add_rolling_features(result)
# #             logger.debug("Added rolling features")

# #         # Add aggregation features
# #         result = self._add_aggregation_features(result)
# #         logger.debug("Added aggregation features")

# #         # Add interaction features
# #         result = self._add_interaction_features(result)
# #         logger.debug("Added interaction features")

# #         # Add seasonal features
# #         if self.time_features:
# #             result = self._add_seasonal_features(result)
# #             logger.debug("Added seasonal features")

# #         # Encode categorical features
# #         result = self._encode_categorical(result)
# #         logger.debug("Encoded categorical features")

# #         # Scale features
# #         result = self._scale_features(result)
# #         logger.debug("Scaled features")

# #         logger.info(f"Feature engineering complete. Final shape: {result.shape}")
# #         return result

# #     def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
# #         """Add time-based features"""
# #         df = df.copy()
# #         if self.date_col in df.columns:
# #             df['day_of_week'] = df[self.date_col].dt.dayofweek
# #             df['month'] = df[self.date_col].dt.month
# #             df['quarter'] = df[self.date_col].dt.quarter
# #             df['year'] = df[self.date_col].dt.year
# #             df['is_weekend'] = (df[self.date_col].dt.dayofweek >= 5).astype(int)
# #             # Simple holiday indicator (weekends + major holidays)
# #             df['days_until_holiday'] = 0  # Placeholder
# #         return df

# #     def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
# #         """Add lag features"""
# #         df = df.copy()
# #         for group in self.group_by:
# #             for lag in self.lag_features:
# #                 df[f'{self.target}_lag_{lag}'] = df.groupby(group)[self.target].shift(lag)
# #                 if 'price' in df.columns:
# #                     df[f'price_lag_{lag}'] = df.groupby(group)['price'].shift(lag)
# #         return df

# #     def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
# #         """Add rolling window features"""
# #         df = df.copy()
# #         for group in self.group_by:
# #             for window in self.rolling_windows:
# #                 df[f'{self.target}_roll_mean_{window}'] = (
# #                     df.groupby(group)[self.target]
# #                     .transform(lambda x: x.rolling(window, min_periods=1).mean())
# #                 )
# #                 df[f'{self.target}_roll_std_{window}'] = (
# #                     df.groupby(group)[self.target]
# #                     .transform(lambda x: x.rolling(window, min_periods=1).std())
# #                 )
# #                 df[f'{self.target}_roll_min_{window}'] = (
# #                     df.groupby(group)[self.target]
# #                     .transform(lambda x: x.rolling(window, min_periods=1).min())
# #                 )
# #                 df[f'{self.target}_roll_max_{window}'] = (
# #                     df.groupby(group)[self.target]
# #                     .transform(lambda x: x.rolling(window, min_periods=1).max())
# #                 )
# #                 if 'price' in df.columns:
# #                     df[f'price_roll_mean_{window}'] = (
# #                         df.groupby(group)['price']
# #                         .transform(lambda x: x.rolling(window, min_periods=1).mean())
# #                     )
# #         return df

# #     def _add_aggregation_features(self, df: pd.DataFrame) -> pd.DataFrame:
# #         """Add aggregation features"""
# #         df = df.copy()
# #         for group in self.group_by:
# #             # Aggregations for target
# #             df[f'{self.target}_mean'] = df.groupby(group)[self.target].transform('mean')
# #             df[f'{self.target}_std'] = df.groupby(group)[self.target].transform('std')
# #             df[f'{self.target}_min'] = df.groupby(group)[self.target].transform('min')
# #             df[f'{self.target}_max'] = df.groupby(group)[self.target].transform('max')

# #             # Aggregations for price
# #             if 'price' in df.columns:
# #                 df['price_mean'] = df.groupby(group)['price'].transform('mean')
# #                 df['price_std'] = df.groupby(group)['price'].transform('std')

# #             # Unique store count per product
# #             if 'store_id' in df.columns:
# #                 df['store_id_nunique'] = df.groupby(group)['store_id'].transform('nunique')
# #         return df

# #     def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
# #         """Add interaction features"""
# #         df = df.copy()
# #         if 'quantity' in df.columns and 'price' in df.columns:
# #             df['revenue'] = df['quantity'] * df['price']
# #             df['log_quantity'] = np.log1p(df['quantity'])
# #             df['log_price'] = np.log1p(df['price'])
# #             df['log_revenue'] = np.log1p(df['revenue'])
# #         return df

# #     def _add_seasonal_features(self, df: pd.DataFrame) -> pd.DataFrame:
# #         """Add seasonal features using sine/cosine transformations"""
# #         df = df.copy()
# #         if self.date_col in df.columns:
# #             # Monthly seasonality
# #             df['month_sin'] = np.sin(2 * np.pi * df[self.date_col].dt.month / 12)
# #             df['month_cos'] = np.cos(2 * np.pi * df[self.date_col].dt.month / 12)

# #             # Weekly seasonality
# #             df['day_of_week_sin'] = np.sin(2 * np.pi * df[self.date_col].dt.dayofweek / 7)
# #             df['day_of_week_cos'] = np.cos(2 * np.pi * df[self.date_col].dt.dayofweek / 7)
# #         return df

# #     def _encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
# #         """
# #         Encode categorical columns using one-hot encoding.

# #         Args:
# #             df: Input DataFrame

# #         Returns:
# #             DataFrame with categorical columns encoded
# #         """
# #         df = df.copy()

# #         # Get categorical columns from config or auto-detect
# #         categorical_cols = self.config.get('categorical_columns', [])
# #         if not categorical_cols:
# #             # Auto-detect categorical columns (object or category dtype)
# #             categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
# #             # Exclude date columns if they are object type
# #             categorical_cols = [col for col in categorical_cols if col != self.date_col]

# #         # If no categorical columns found, return original dataframe
# #         if not categorical_cols:
# #             return df

# #         # One-hot encode categorical columns using pandas
# #         for col in categorical_cols:
# #             if col in df.columns:
# #                 # Create dummy variables
# #                 dummies = pd.get_dummies(df[col], prefix=col, drop_first=False)
# #                 # Drop original column and concatenate dummies
# #                 df = df.drop(columns=[col])
# #                 df = pd.concat([df, dummies], axis=1)

# #         return df

# #     def _scale_features(self, df: pd.DataFrame) -> pd.DataFrame:
# #         """Scale numerical features"""
# #         df = df.copy()

# #         # Select numerical columns (excluding target and categorical encoded)
# #         exclude_cols = [self.target, self.date_col]
# #         if self.date_col in df.columns:
# #             exclude_cols.append(self.date_col)

# #         numerical_cols = df.select_dtypes(include=[np.number]).columns.tolist()
# #         numerical_cols = [col for col in numerical_cols if col not in exclude_cols]

# #         if numerical_cols:
# #             if self.scaler is None:
# #                 self.scaler = StandardScaler()
# #                 self.scaler.fit(df[numerical_cols])

# #             df[numerical_cols] = self.scaler.transform(df[numerical_cols])

# #         return df


# # class FeatureSelector:
# #     """Feature selection class"""

# #     def __init__(self, config: Dict[str, Any]):
# #         """Initialize FeatureSelector"""
# #         self.config = config
# #         self.method = config.get('method', 'importance')
# #         self.num_features = config.get('num_features', 10)

# #     def select_features(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
# #         """
# #         Select top features based on specified method.

# #         Args:
# #             X: Feature DataFrame
# #             y: Target Series

# #         Returns:
# #             List of selected feature names
# #         """
# #         if self.method == 'importance':
# #             return self._importance_based_selection(X, y)
# #         elif self.method == 'rfe':
# #             return self._rfe_selection(X, y)
# #         elif self.method == 'correlation':
# #             return self._correlation_selection(X, y)
# #         else:
# #             raise ValueError(f"Unsupported selection method: {self.method}")

# #     def _importance_based_selection(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
# #         """Select features based on importance"""
# #         from sklearn.ensemble import RandomForestRegressor

# #         # Handle missing values
# #         X_clean = X.fillna(X.mean())

# #         model = RandomForestRegressor(n_estimators=100, random_state=42)
# #         model.fit(X_clean, y)

# #         # Get feature importances
# #         importances = model.feature_importances_
# #         feature_importance = pd.DataFrame({
# #             'feature': X.columns,
# #             'importance': importances
# #         }).sort_values('importance', ascending=False)

# #         # Select top features
# #         selected = feature_importance.head(self.num_features)['feature'].tolist()
# #         return selected

# #     def _rfe_selection(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
# #         """Select features using RFE"""
# #         from sklearn.feature_selection import RFE
# #         from sklearn.ensemble import RandomForestRegressor

# #         X_clean = X.fillna(X.mean())
# #         model = RandomForestRegressor(n_estimators=100, random_state=42)
# #         rfe = RFE(model, n_features_to_select=self.num_features)
# #         rfe.fit(X_clean, y)

# #         # Get selected features
# #         selected = X.columns[rfe.support_].tolist()
# #         return selected

# #     def _correlation_selection(self, X: pd.DataFrame, y: pd.Series) -> List[str]:
# #         """Select features based on correlation with target"""
# #         # Handle missing values
# #         X_clean = X.fillna(X.mean())

# #         # Calculate correlations
# #         correlations = X_clean.apply(lambda x: x.corr(y))

# #         # Select top features by absolute correlation
# #         selected = correlations.abs().sort_values(ascending=False).head(self.num_features).index.tolist()
# #         return selected


"""
Feature Engineering - 50+ features
"""

from typing import Any, cast

import numpy as np
import pandas as pd
import structlog
from sklearn.preprocessing import OneHotEncoder, StandardScaler

logger = structlog.get_logger()


class FeatureEngineer:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.time_features = config.get("time_features", True)
        self.lag_features = config.get("lag_features", [1, 7, 14, 30])
        self.rolling_windows = config.get("rolling_windows", [7, 14, 30, 90])
        self.group_by = config.get("group_by", ["product_id"])
        self.target = config.get("target", "quantity")
        self.date_col = config.get("date_col", "date")
        self.scaler: StandardScaler | None = None
        self.encoder: OneHotEncoder | None = None

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create all features for the dataset."""
        df = df.copy()
        if self.date_col in df.columns:
            df = df.sort_values(self.date_col)

        if self.time_features:
            df = self._add_time_features(df)

        df = self._add_lag_features(df)
        df = self._add_rolling_features(df)
        df = self._add_aggregation_features(df)
        df = self._add_interaction_features(df)
        df = self._encode_categorical(df)
        df = self._scale_features(df)
        df = self._add_seasonal_features(df)

        return df

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features from date column."""
        if self.date_col not in df.columns:
            return df
        dt = pd.to_datetime(df[self.date_col])
        df["day_of_week"] = dt.dt.dayofweek
        df["day_of_month"] = dt.dt.day
        df["day_of_year"] = dt.dt.dayofyear
        df["week_of_year"] = dt.dt.isocalendar().week
        df["month"] = dt.dt.month
        df["quarter"] = dt.dt.quarter
        df["year"] = dt.dt.year
        df["is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)
        df["is_month_start"] = dt.dt.is_month_start.astype(int)
        df["is_month_end"] = dt.dt.is_month_end.astype(int)
        df["is_quarter_start"] = dt.dt.is_quarter_start.astype(int)
        df["is_quarter_end"] = dt.dt.is_quarter_end.astype(int)
        df["days_until_holiday"] = self._calculate_holiday_distance(dt)
        df["weeks_until_holiday"] = df["days_until_holiday"] // 7
        return df

    def _calculate_holiday_distance(self, dt: pd.Series) -> pd.Series:
        """Calculate distance to nearest holiday."""
        holidays = pd.to_datetime(["2024-01-01", "2024-12-25", "2024-11-28", "2024-07-04"])

        def distance_to_holiday(date: pd.Timestamp) -> int:
            min_dist = min(abs(date - h).days for h in holidays)
            return int(min_dist)  # Cast to int to ensure type safety

        return dt.apply(distance_to_holiday)

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add lag features for the target and price."""
        for lag in self.lag_features:
            df[f"{self.target}_lag_{lag}"] = df.groupby(self.group_by)[self.target].shift(lag)
        if "price" in df.columns:
            for lag in self.lag_features[:3]:
                df[f"price_lag_{lag}"] = df.groupby(self.group_by)["price"].shift(lag)
        return df

    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rolling statistics features."""
        for window in self.rolling_windows:
            df[f"{self.target}_roll_mean_{window}"] = (
                df.groupby(self.group_by)[self.target]
                .rolling(window)
                .mean()
                .reset_index(level=0, drop=True)
            )
            df[f"{self.target}_roll_std_{window}"] = (
                df.groupby(self.group_by)[self.target]
                .rolling(window)
                .std()
                .reset_index(level=0, drop=True)
            )
            df[f"{self.target}_roll_min_{window}"] = (
                df.groupby(self.group_by)[self.target]
                .rolling(window)
                .min()
                .reset_index(level=0, drop=True)
            )
            df[f"{self.target}_roll_max_{window}"] = (
                df.groupby(self.group_by)[self.target]
                .rolling(window)
                .max()
                .reset_index(level=0, drop=True)
            )
            if "price" in df.columns:
                df[f"price_roll_mean_{window}"] = (
                    df.groupby(self.group_by)["price"]
                    .rolling(window)
                    .mean()
                    .reset_index(level=0, drop=True)
                )
        return df

    def _add_aggregation_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add aggregation features grouped by product/other columns."""
        agg_dict = {
            self.target: ["mean", "std", "min", "max", "sum", "count"],
            "price": ["mean", "std", "min", "max"],
        }
        if "store_id" in df.columns:
            agg_dict["store_id"] = ["nunique"]
        aggregations = df.groupby(self.group_by).agg(agg_dict)
        aggregations.columns = ["_".join(col).strip() for col in aggregations.columns.values]
        aggregations = aggregations.reset_index()
        df = df.merge(aggregations, on=self.group_by, how="left")
        return df

    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add interaction features between existing features."""
        if self.target in df.columns and "price" in df.columns:
            df["revenue"] = df[self.target] * df["price"]
            df["log_quantity"] = np.log1p(df[self.target])
            df["log_price"] = np.log1p(df["price"])
            df["log_revenue"] = np.log1p(df["revenue"])
        if "quantity_lag_1" in df.columns:
            df["quantity_change"] = df[self.target] - df["quantity_lag_1"]
            df["quantity_change_pct"] = (df["quantity_change"] / (df["quantity_lag_1"] + 1)) * 100
        return df

    def _add_seasonal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add seasonal features using sine/cosine transformations."""
        if self.date_col not in df.columns:
            return df
        dt = pd.to_datetime(df[self.date_col])
        df["month_sin"] = np.sin(2 * np.pi * dt.dt.month / 12)
        df["month_cos"] = np.cos(2 * np.pi * dt.dt.month / 12)
        df["day_of_week_sin"] = np.sin(2 * np.pi * dt.dt.dayofweek / 7)
        df["day_of_week_cos"] = np.cos(2 * np.pi * dt.dt.dayofweek / 7)
        return df

    def _encode_categorical(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical variables using one-hot encoding."""
        # Get categorical columns excluding group_by columns
        categorical_cols = [
            c
            for c in df.select_dtypes(include=["object", "category"]).columns
            if c not in self.group_by
        ]
        if not categorical_cols:
            return df

        if self.encoder is None:
            self.encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
            encoded = self.encoder.fit_transform(df[categorical_cols])
            feature_names = cast(list[str], self.encoder.get_feature_names_out(categorical_cols))
        else:
            encoded = self.encoder.transform(df[categorical_cols])
            feature_names = cast(list[str], self.encoder.get_feature_names_out(categorical_cols))

        encoded_df = pd.DataFrame(encoded, columns=feature_names, index=df.index)
        df = pd.concat([df, encoded_df], axis=1)
        df = df.drop(columns=categorical_cols)
        return df

    def _scale_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scale numerical features using StandardScaler."""
        numerical_cols = [
            c for c in df.select_dtypes(include=[np.number]).columns if c not in self.group_by
        ]
        if not numerical_cols:
            return df

        if self.scaler is None:
            self.scaler = StandardScaler()
            df[numerical_cols] = self.scaler.fit_transform(df[numerical_cols])
        else:
            df[numerical_cols] = self.scaler.transform(df[numerical_cols])
        return df


class FeatureSelector:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.method = config.get("method", "importance")
        self.num_features = config.get("num_features", 50)

    def select_features(self, x: pd.DataFrame, y: pd.Series) -> list[str]:
        """
        Select the most important features using various methods.

        Args:
            x: Feature matrix
            y: Target variable

        Returns:
            List of selected feature names
        """
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.feature_selection import RFE

        if self.method == "importance":
            model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            model.fit(x, y)
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1]
            selected = x.columns[indices[: self.num_features]].tolist()
            return cast(list[str], selected)
        elif self.method == "rfe":
            model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            rfe = RFE(model, n_features_to_select=self.num_features)
            rfe.fit(x, y)
            selected = x.columns[rfe.support_].tolist()
            return cast(list[str], selected)
        else:
            correlations = x.corrwith(y).abs().sort_values(ascending=False)
            selected = correlations.head(self.num_features).index.tolist()
            return cast(list[str], selected)
