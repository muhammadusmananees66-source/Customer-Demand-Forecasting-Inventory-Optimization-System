"""
Evaluation & Tuning Layer - Metrics, Hyperparameter Tuning, Ablation Study
"""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
import optuna
from optuna.samplers import TPESampler
from typing import Dict, List, Tuple
import mlflow
import logging

logger = logging.getLogger(__name__)

class ModelEvaluation:
    """Comprehensive model evaluation"""

    def __init__(self):
        self.metrics_history = []

    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """Calculate all evaluation metrics"""

        metrics = {
            'MAE': mean_absolute_error(y_true, y_pred),
            'MSE': mean_squared_error(y_true, y_pred),
            'RMSE': np.sqrt(mean_squared_error(y_true, y_pred)),
            'MAPE': np.mean(np.abs((y_true - y_pred) / y_true)) * 100,
            'R2': r2_score(y_true, y_pred)
        }

        # Additional demand-specific metrics
        metrics['WMAPE'] = self._weighted_mape(y_true, y_pred)
        metrics['Bias'] = np.mean(y_pred - y_true)
        metrics['Prediction_Interval_Coverage'] = self._calculate_pi_coverage(y_true, y_pred)

        return metrics

    def _weighted_mape(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Weighted MAPE (better for intermittent demand)"""
        return np.sum(np.abs(y_true - y_pred)) / np.sum(y_true) * 100

    def _calculate_pi_coverage(self, y_true: np.ndarray, y_pred: np.ndarray,
                               interval: float = 0.8) -> float:
        """Calculate prediction interval coverage"""
        residuals = y_true - y_pred
        quantile = np.percentile(np.abs(residuals), interval * 100)
        coverage = np.mean(np.abs(residuals) <= quantile)
        return coverage

    def cross_validation(self, model, X: pd.DataFrame, y: pd.Series,
                         cv_folds: int = 5) -> Dict:
        """Time series cross-validation"""

        tscv = TimeSeriesSplit(n_splits=cv_folds)

        cv_scores = {
            'MAE': [],
            'RMSE': [],
            'MAPE': []
        }

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)

            cv_scores['MAE'].append(mean_absolute_error(y_val, y_pred))
            cv_scores['RMSE'].append(np.sqrt(mean_squared_error(y_val, y_pred)))
            cv_scores['MAPE'].append(np.mean(np.abs((y_val - y_pred) / y_val)) * 100)

        results = {
            'mean_mae': np.mean(cv_scores['MAE']),
            'std_mae': np.std(cv_scores['MAE']),
            'mean_rmse': np.mean(cv_scores['RMSE']),
            'std_rmse': np.std(cv_scores['RMSE']),
            'mean_mape': np.mean(cv_scores['MAPE']),
            'std_mape': np.std(cv_scores['MAPE'])
        }

        return results

    def compare_models(self, models: Dict, X_test: pd.DataFrame,
                       y_test: pd.Series) -> pd.DataFrame:
        """Compare multiple models"""

        comparison = []

        for name, model in models.items():
            y_pred = model.predict(X_test)
            metrics = self.calculate_metrics(y_test, y_pred)
            metrics['Model'] = name
            comparison.append(metrics)

        return pd.DataFrame(comparison)

class HyperparameterTuning:
    """Hyperparameter optimization with Optuna"""

    def __init__(self, model_type: str = 'xgboost'):
        self.model_type = model_type
        self.study = None

    def objective_xgboost(self, trial, X_train, y_train, X_val, y_val):
        """Optuna objective for XGBoost"""

        params = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
            'max_depth': trial.suggest_int('max_depth', 3, 12),
            'learning_rate': trial.suggest_float('learning_rate', 0.001, 0.1, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'reg_alpha': trial.suggest_float('reg_alpha', 0, 2),
            'reg_lambda': trial.suggest_float('reg_lambda', 0, 2),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'gamma': trial.suggest_float('gamma', 0, 0.5)
        }

        model = xgb.XGBRegressor(**params, random_state=42)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

        y_pred = model.predict(X_val)
        score = mean_absolute_error(y_val, y_pred)

        return score

    def objective_lstm(self, trial, train_loader, val_loader):
        """Optuna objective for LSTM"""

        params = {
            'hidden_size': trial.suggest_int('hidden_size', 64, 512),
            'num_layers': trial.suggest_int('num_layers', 1, 4),
            'learning_rate': trial.suggest_float('learning_rate', 0.0001, 0.01, log=True),
            'dropout': trial.suggest_float('dropout', 0.1, 0.5),
            'batch_size': trial.suggest_categorical('batch_size', [32, 64, 128])
        }

        # Build and train model
        model = self._build_lstm_model(params)

        # Training logic
        val_loss = self._train_lstm_model(model, train_loader, val_loader, params)

        return val_loss

    def optimize(self, X_train, y_train, X_val, y_val, n_trials: int = 100):
        """Run hyperparameter optimization"""

        self.study = optuna.create_study(
            direction='minimize',
            sampler=TPESampler(),
            pruner=optuna.pruners.MedianPruner()
        )

        if self.model_type == 'xgboost':
            self.study.optimize(
                lambda trial: self.objective_xgboost(trial, X_train, y_train, X_val, y_val),
                n_trials=n_trials,
                show_progress_bar=True
            )

        best_params = self.study.best_params
        best_value = self.study.best_value

        # Log to MLflow
        with mlflow.start_run(run_name="hyperparameter_tuning"):
            mlflow.log_params(best_params)
            mlflow.log_metric("best_validation_mae", best_value)

        return best_params, best_value

    def plot_optimization_history(self):
        """Plot optimization history"""
        import matplotlib.pyplot as plt

        fig = optuna.visualization.plot_optimization_history(self.study)
        fig.show()

class AblationStudy:
    """Ablation study to understand feature importance"""

    def __init__(self, model, feature_names: List[str]):
        self.model = model
        self.feature_names = feature_names

    def run_ablation(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """Remove each feature and measure impact"""

        baseline_score = self._evaluate_model(X, y)
        results = []

        for feature in self.feature_names:
            # Remove feature
            X_ablated = X.drop(columns=[feature])

            # Retrain model
            self.model.fit(X_ablated, y)
            score = self._evaluate_model(X_ablated, y)

            # Calculate impact
            impact = (baseline_score - score) / baseline_score * 100

            results.append({
                'feature': feature,
                'baseline_score': baseline_score,
                'score_without_feature': score,
                'impact_percent': impact,
                'importance': impact / len(self.feature_names) * 100
            })

        results_df = pd.DataFrame(results).sort_values('impact_percent', ascending=False)

        # Log results
        with mlflow.start_run(run_name="ablation_study"):
            for _, row in results_df.iterrows():
                mlflow.log_metric(f"impact_{row['feature']}", row['impact_percent'])

        return results_df

    def _evaluate_model(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Evaluate model performance"""
        y_pred = self.model.predict(X)
        return mean_absolute_error(y, y_pred)