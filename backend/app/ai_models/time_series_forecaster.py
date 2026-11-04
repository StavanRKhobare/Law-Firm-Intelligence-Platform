"""
Time Series Forecasting for Crime Prediction
Uses ARIMA and Prophet for forecasting future crime trends
"""
import os
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.seasonal import seasonal_decompose
try:  # prophet is optional; only ARIMA is used by the API
    from prophet import Prophet
except ImportError:
    Prophet = None
import joblib
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class CrimeTimeSeriesForecaster:
    """
    Forecasts future crime trends using:
    1. ARIMA for univariate time series
    2. SARIMAX for seasonal patterns
    3. Prophet for complex seasonality
    """
    
    def __init__(self, model_type: str = 'arima', model_dir: str = "models/forecasting"):
        """
        Initialize the time series forecaster
        
        Args:
            model_type: 'arima', 'sarimax', or 'prophet'
            model_dir: Directory to save/load models
        """
        self.model_type = model_type
        self.model_dir = model_dir
        self.model = None
        self.forecast_results = None
        
    def prepare_time_series(self, df: pd.DataFrame, 
                           date_col: str = 'date_occ',
                           value_col: str = 'crime_count',
                           frequency: str = 'D') -> pd.DataFrame:
        """
        Prepare time series data
        
        Args:
            df: DataFrame with dates and crime counts
            date_col: Date column name
            value_col: Value column name
            frequency: 'D' (daily), 'W' (weekly), 'M' (monthly)
            
        Returns:
            Prepared time series DataFrame
        """
        # Ensure date is datetime
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
        
        # Set date as index
        df = df.set_index(date_col)
        
        # Resample to desired frequency
        if frequency == 'D':
            ts = df[value_col].resample('D').sum()
        elif frequency == 'W':
            ts = df[value_col].resample('W').sum()
        elif frequency == 'M':
            ts = df[value_col].resample('ME').sum()
        else:
            ts = df[value_col]
        
        # Fill missing values
        ts = ts.fillna(0)
        
        # Create DataFrame
        ts_df = pd.DataFrame({
            'date': ts.index,
            'value': ts.values
        })
        
        return ts_df
    
    def analyze_seasonality(self, ts: pd.Series, period: int = 30) -> Dict:
        """
        Analyze seasonal patterns in the time series
        
        Args:
            ts: Time series data
            period: Seasonality period (e.g., 7 for weekly, 30 for monthly)
            
        Returns:
            Dictionary with decomposition results
        """
        if len(ts) < period * 2:
            print(f"Warning: Time series too short for seasonality analysis (need at least {period * 2} points)")
            return {}
        
        # Seasonal decomposition
        decomposition = seasonal_decompose(ts, model='additive', period=period)
        
        analysis = {
            'trend_strength': float(decomposition.trend.std() / ts.std()) if ts.std() > 0 else 0,
            'seasonal_strength': float(decomposition.seasonal.std() / ts.std()) if ts.std() > 0 else 0,
            'residual_strength': float(decomposition.resid.std() / ts.std()) if ts.std() > 0 else 0,
            'has_trend': decomposition.trend.std() > 0.1,
            'has_seasonality': decomposition.seasonal.std() > 0.1
        }
        
        return analysis
    
    def train_arima(self, ts: pd.Series, order: Tuple[int, int, int] = (5, 1, 0),
                    auto_order: bool = True):
        """
        Train ARIMA model
        
        Args:
            ts: Time series data
            order: (p, d, q) order for ARIMA
            auto_order: If True, automatically find best order
        """
        if auto_order:
            print("Finding optimal ARIMA order...")
            try:
                from pmdarima import auto_arima
                auto_model = auto_arima(
                    ts,
                    start_p=1, start_q=1,
                    max_p=5, max_q=5,
                    m=1,  # No seasonality for basic ARIMA
                    seasonal=False,
                    trace=True,
                    error_action='ignore',
                    suppress_warnings=True,
                    stepwise=True
                )
                order = auto_model.order
                print(f"Optimal order: {order}")
            except Exception as e:
                print(f"Auto ARIMA failed: {e}, using default order {order}")
        
        print(f"Training ARIMA{order} model...")
        self.model = ARIMA(ts, order=order)
        self.model = self.model.fit()
        
        print("\nModel Summary:")
        print(self.model.summary())
        
        # Model diagnostics
        print("\nAIC:", self.model.aic)
        print("BIC:", self.model.bic)
        
        return self.model
    
    def train_sarimax(self, ts: pd.Series, 
                      order: Tuple[int, int, int] = (1, 1, 1),
                      seasonal_order: Tuple[int, int, int, int] = (1, 1, 1, 7),
                      auto_order: bool = True):
        """
        Train SARIMAX model (ARIMA with seasonality)
        
        Args:
            ts: Time series data
            order: (p, d, q) order for non-seasonal part
            seasonal_order: (P, D, Q, s) order for seasonal part
            auto_order: If True, automatically find best order
        """
        if auto_order:
            print("Finding optimal SARIMAX order...")
            try:
                from pmdarima import auto_arima
                auto_model = auto_arima(
                    ts,
                    start_p=1, start_q=1,
                    max_p=3, max_q=3,
                    m=seasonal_order[3],  # Seasonal period
                    seasonal=True,
                    start_P=0, start_Q=0,
                    max_P=2, max_Q=2,
                    trace=True,
                    error_action='ignore',
                    suppress_warnings=True,
                    stepwise=True
                )
                order = auto_model.order
                seasonal_order = auto_model.seasonal_order
                print(f"Optimal order: {order} x {seasonal_order}")
            except Exception as e:
                print(f"Auto SARIMAX failed: {e}, using default orders")
        
        print(f"Training SARIMAX{order}x{seasonal_order} model...")
        self.model = SARIMAX(ts, order=order, seasonal_order=seasonal_order)
        self.model = self.model.fit(disp=False)
        
        print("\nModel Summary:")
        print(self.model.summary())
        
        return self.model
    
    def train_prophet(self, ts_df: pd.DataFrame):
        """
        Train Prophet model
        
        Args:
            ts_df: DataFrame with 'date' and 'value' columns
        """
        # Prophet requires specific column names
        prophet_df = ts_df.rename(columns={'date': 'ds', 'value': 'y'})
        
        print("Training Prophet model...")
        self.model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
            changepoint_prior_scale=0.05
        )
        
        self.model.fit(prophet_df)
        
        print("Prophet model trained successfully")
        
        return self.model
    
    def forecast(self, periods: int = 30, frequency: str = 'D') -> pd.DataFrame:
        """
        Generate forecast
        
        Args:
            periods: Number of periods to forecast
            frequency: Forecast frequency ('D', 'W', 'M')
            
        Returns:
            DataFrame with forecast results
        """
        if self.model is None:
            raise ValueError("Model not trained. Train a model first.")
        
        if self.model_type in ['arima', 'sarimax']:
            # ARIMA/SARIMAX forecast
            forecast_result = self.model.forecast(steps=periods)
            
            # Get confidence intervals
            forecast_ci = self.model.get_forecast(steps=periods).conf_int()
            
            # Create forecast dataframe
            last_date = self.model.data.dates[-1]
            if frequency == 'D':
                forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=periods, freq='D')
            elif frequency == 'W':
                forecast_dates = pd.date_range(start=last_date + timedelta(weeks=1), periods=periods, freq='W')
            elif frequency == 'M':
                forecast_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=periods, freq='ME')
            
            forecast_df = pd.DataFrame({
                'date': forecast_dates,
                'forecast': forecast_result.values,
                'lower_bound': forecast_ci.iloc[:, 0].values,
                'upper_bound': forecast_ci.iloc[:, 1].values
            })
            
        elif self.model_type == 'prophet':
            # Prophet forecast
            future = self.model.make_future_dataframe(periods=periods, freq=frequency)
            forecast = self.model.predict(future)
            
            # Get only future predictions
            forecast_df = forecast[forecast['ds'] > self.model.history['ds'].max()].copy()
            forecast_df = forecast_df.rename(columns={
                'ds': 'date',
                'yhat': 'forecast',
                'yhat_lower': 'lower_bound',
                'yhat_upper': 'upper_bound'
            })[['date', 'forecast', 'lower_bound', 'upper_bound']]
        
        # Ensure no negative forecasts
        forecast_df['forecast'] = forecast_df['forecast'].clip(lower=0)
        forecast_df['lower_bound'] = forecast_df['lower_bound'].clip(lower=0)
        forecast_df['upper_bound'] = forecast_df['upper_bound'].clip(lower=0)
        
        self.forecast_results = forecast_df
        
        return forecast_df
    
    def evaluate_model(self, ts: pd.Series, test_size: int = 30) -> Dict:
        """
        Evaluate model on test set
        
        Args:
            ts: Complete time series
            test_size: Number of periods for testing
            
        Returns:
            Dictionary with evaluation metrics
        """
        # Split into train and test
        train = ts[:-test_size]
        test = ts[-test_size:]
        
        # Retrain on training data
        if self.model_type == 'arima':
            temp_model = ARIMA(train, order=(5, 1, 0)).fit()
        elif self.model_type == 'sarimax':
            temp_model = SARIMAX(train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7)).fit()
        
        # Forecast
        forecast = temp_model.forecast(steps=test_size)
        
        # Calculate metrics
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        
        mae = mean_absolute_error(test, forecast)
        rmse = np.sqrt(mean_squared_error(test, forecast))
        mape = np.mean(np.abs((test - forecast) / (test + 1))) * 100  # +1 to avoid division by zero
        
        metrics = {
            'MAE': float(mae),
            'RMSE': float(rmse),
            'MAPE': float(mape),
            'R2': float(r2_score(test, forecast)) if len(test) > 1 else 0
        }
        
        print("\n=== Model Evaluation ===")
        for metric, value in metrics.items():
            print(f"{metric}: {value:.4f}")
        
        return metrics
    
    def detect_anomalies(self, ts: pd.Series, threshold: float = 2.0) -> pd.DataFrame:
        """
        Detect anomalies in time series using residuals
        
        Args:
            ts: Time series data
            threshold: Number of standard deviations for anomaly detection
            
        Returns:
            DataFrame with anomaly flags
        """
        if self.model is None:
            raise ValueError("Model not trained.")
        
        # Get residuals
        if self.model_type in ['arima', 'sarimax']:
            residuals = self.model.resid
        else:
            return pd.DataFrame()  # Prophet handles this differently
        
        # Calculate threshold
        mean_resid = residuals.mean()
        std_resid = residuals.std()
        upper_bound = mean_resid + threshold * std_resid
        lower_bound = mean_resid - threshold * std_resid
        
        # Identify anomalies
        anomalies = pd.DataFrame({
            'date': ts.index,
            'value': ts.values,
            'residual': residuals.values,
            'is_anomaly': (residuals > upper_bound) | (residuals < lower_bound)
        })
        
        anomaly_count = anomalies['is_anomaly'].sum()
        print(f"\nDetected {anomaly_count} anomalies ({(anomaly_count/len(ts)*100):.2f}% of data)")
        
        return anomalies
    
    def get_trend_analysis(self, forecast_df: pd.DataFrame) -> Dict:
        """
        Analyze trends in the forecast
        
        Args:
            forecast_df: Forecast DataFrame
            
        Returns:
            Dictionary with trend analysis
        """
        forecast_values = forecast_df['forecast'].values
        
        # Calculate trend
        trend_slope = np.polyfit(range(len(forecast_values)), forecast_values, 1)[0]
        
        # Categorize trend
        if trend_slope > 0.5:
            trend_category = "Strongly Increasing"
        elif trend_slope > 0.1:
            trend_category = "Moderately Increasing"
        elif trend_slope > -0.1:
            trend_category = "Stable"
        elif trend_slope > -0.5:
            trend_category = "Moderately Decreasing"
        else:
            trend_category = "Strongly Decreasing"
        
        # Calculate statistics
        analysis = {
            'trend_slope': float(trend_slope),
            'trend_category': trend_category,
            'mean_forecast': float(forecast_values.mean()),
            'std_forecast': float(forecast_values.std()),
            'min_forecast': float(forecast_values.min()),
            'max_forecast': float(forecast_values.max()),
            'total_predicted_crimes': int(forecast_values.sum())
        }
        
        return analysis
    
    def save_model(self, filepath: str = None):
        """Save trained model to disk"""
        if filepath is None:
            filepath = f"{self.model_dir}/forecast_{self.model_type}.pkl"
        
        model_data = {
            'model': self.model,
            'model_type': self.model_type,
            'forecast_results': self.forecast_results
        }
        
        joblib.dump(model_data, filepath)
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str = None):
        """Load trained model from disk"""
        if filepath is None:
            filepath = f"{self.model_dir}/forecast_{self.model_type}.pkl"
        
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.model_type = model_data['model_type']
        self.forecast_results = model_data.get('forecast_results')
        
        print(f"Model loaded from {filepath}")


# Example usage
if __name__ == "__main__":
    from data_extractor import CrimeDataExtractor
    
    # Database connection
    DB_URL = os.environ["DATABASE_URL"]

    
    # Extract data
    extractor = CrimeDataExtractor(DB_URL)
    df_ts = extractor.get_time_series_data(frequency='D')
    
    print(f"Time series length: {len(df_ts)} days")
    print(df_ts.head())
    
    # Test ARIMA
    print("\n" + "="*50)
    print("TESTING ARIMA MODEL")
    print("="*50)
    
    arima_forecaster = CrimeTimeSeriesForecaster(model_type='arima')
    ts = df_ts.set_index('date_occ')['crime_count']
    
    # Analyze seasonality
    seasonality = arima_forecaster.analyze_seasonality(ts, period=7)
    print("\nSeasonality Analysis:")
    print(json.dumps(seasonality, indent=2))
    
    # Train model
    arima_forecaster.train_arima(ts, auto_order=True)
    
    # Evaluate
    metrics = arima_forecaster.evaluate_model(ts, test_size=30)
    
    # Forecast
    forecast_df = arima_forecaster.forecast(periods=30, frequency='D')
    print("\nForecast (next 30 days):")
    print(forecast_df.head(10))
    
    # Trend analysis
    trend = arima_forecaster.get_trend_analysis(forecast_df)
    print("\nTrend Analysis:")
    print(json.dumps(trend, indent=2))
    
    # Save model
    arima_forecaster.save_model()
    
    extractor.close()