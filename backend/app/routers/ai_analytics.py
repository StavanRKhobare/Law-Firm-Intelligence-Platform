"""
FastAPI Router for AI Analytics
Provides endpoints for crime prediction, hotspot analysis, and forecasting
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from ai_models.data_extractor import CrimeDataExtractor
    from ai_models.hotspot_predictor import CrimeHotspotPredictor
    from ai_models.time_series_forecaster import CrimeTimeSeriesForecaster
    ML_AVAILABLE = True
    ML_IMPORT_ERROR = None
except Exception as e:  # sklearn/xgboost/prophet etc. are optional (see requirements-ml.txt)
    CrimeDataExtractor = CrimeHotspotPredictor = CrimeTimeSeriesForecaster = None
    ML_AVAILABLE = False
    ML_IMPORT_ERROR = e

# The matter classifier only needs scikit-learn, so it is imported on its own.
try:
    from ai_models.matter_classifier import MatterTypeClassifier, DEFAULT_MODEL as MATTER_MODEL_PATH
    CLASSIFIER_IMPORT_ERROR = None
except Exception as e:
    MatterTypeClassifier, MATTER_MODEL_PATH = None, None
    CLASSIFIER_IMPORT_ERROR = e

_matter_classifier = None


def _get_matter_classifier():
    """Load the trained matter classifier once and reuse it."""
    global _matter_classifier
    if MatterTypeClassifier is None:
        raise HTTPException(status_code=503, detail=f"Matter classifier unavailable: scikit-learn not installed ({CLASSIFIER_IMPORT_ERROR}).")
    if _matter_classifier is None:
        if not os.path.exists(MATTER_MODEL_PATH):
            raise HTTPException(status_code=503, detail="Matter classifier not trained. Run: python train_models.py --model classifier")
        _matter_classifier = MatterTypeClassifier().load()
    return _matter_classifier


def _require_ml():
    """Guard: AI endpoints need optional ML deps (pip install -r requirements-ml.txt)."""
    if not ML_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=f"AI models unavailable: optional ML dependencies not installed ({ML_IMPORT_ERROR}). "
            "Install them with: pip install -r requirements-ml.txt",
        )

router = APIRouter(prefix="/api/v1/ai", tags=["AI Analytics"])

from ..config import settings
from ..core.security import require_role

DB_URL = settings.DATABASE_URL


# ============= Response Models =============

class HotspotLocation(BaseModel):
    location_id: int
    landmark: str
    city: str
    district: str
    risk_score: float
    risk_category: str
    historical_crimes: int
    recent_crimes: int
    predicted_future_crimes: float


class HotspotAnalysisResponse(BaseModel):
    generated_at: str
    total_locations_analyzed: int
    high_risk_locations: int
    top_hotspots: List[HotspotLocation]
    risk_distribution: Dict[str, int]
    avg_risk_score: float
    max_risk_score: float


class MatterTypePrediction(BaseModel):
    prediction: str
    confidence: float
    is_confident: bool
    top_3_predictions: List[Dict[str, Any]]


class MatterClassificationRequest(BaseModel):
    description: str = Field(..., min_length=20, description="Facts or summary of the matter")


class ForecastPoint(BaseModel):
    date: str
    forecast: float
    lower_bound: float
    upper_bound: float


class ForecastResponse(BaseModel):
    forecast_period_days: int
    forecast_data: List[ForecastPoint]
    trend_analysis: Dict[str, Any]
    total_predicted_crimes: int


class TrendAnalysis(BaseModel):
    location_id: int
    landmark: str
    city: str
    current_monthly_avg: float
    predicted_crimes_next_period: float
    trend: str


# ============= Endpoints =============

@router.get("/hotspots", response_model=HotspotAnalysisResponse, dependencies=[Depends(require_role(["admin"]))])
async def get_crime_hotspots(
    top_n: int = Query(10, description="Number of top hotspots to return"),
    min_crimes: int = Query(1, description="Minimum number of crimes for a location")
):
    """
    Analyze and return crime hotspots with risk scores
    
    Returns top N locations with highest crime risk based on:
    - Historical crime density
    - Recent crime activity
    - Crime diversity
    - Open case ratios
    """
    _require_ml()
    try:
        # Extract data
        extractor = CrimeDataExtractor(DB_URL)
        df_crimes = extractor.get_crime_cases_with_location()
        df_locations = extractor.get_location_crime_counts()
        
        # Filter by minimum crimes
        df_locations = df_locations[df_locations['total_crimes'] >= min_crimes]
        
        # Initialize predictor
        predictor = CrimeHotspotPredictor()
        
        # Prepare features and train model
        features = predictor.prepare_features(df_crimes, df_locations)
        predictor.train_risk_model(features)
        
        # Calculate risk scores
        risk_scores = predictor.calculate_risk_scores(features)
        
        # Predict trends
        trends = predictor.predict_hotspot_trends(features, days_ahead=30)
        
        # Generate report
        report = predictor.generate_hotspot_report(risk_scores, trends)
        report['top_hotspots'] = report['top_hotspots'][:top_n]

        extractor.close()

        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hotspot analysis failed: {str(e)}")


@router.get("/hotspots/trends", response_model=List[TrendAnalysis], dependencies=[Depends(require_role(["admin"]))])
async def get_hotspot_trends(
    days_ahead: int = Query(30, description="Number of days to predict ahead"),
    top_n: int = Query(10, description="Number of locations to return")
):
    """
    Predict crime trends for each location
    
    Returns predicted crime counts for the next N days
    """
    _require_ml()
    try:
        extractor = CrimeDataExtractor(DB_URL)
        df_crimes = extractor.get_crime_cases_with_location()
        df_locations = extractor.get_location_crime_counts()
        
        predictor = CrimeHotspotPredictor()
        features = predictor.prepare_features(df_crimes, df_locations)
        predictor.train_risk_model(features)
        
        trends = predictor.predict_hotspot_trends(features, days_ahead=days_ahead)
        
        extractor.close()
        
        # Convert to list of dicts
        trends_list = trends.head(top_n).to_dict('records')
        
        return trends_list
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trend prediction failed: {str(e)}")


@router.post("/classify/matter-type", response_model=MatterTypePrediction)
async def classify_matter_type(request: MatterClassificationRequest):
    """
    Predict the matter type (Criminal, Civil, Family, Corporate, Constitutional)
    from a free-text description of the matter.
    """
    classifier = _get_matter_classifier()
    return classifier.predict(request.description)


@router.get("/classify/matter-type/info")
async def matter_classifier_info():
    """Labels and held-out test metrics of the trained matter classifier."""
    classifier = _get_matter_classifier()
    m = classifier.metrics
    return {
        "labels": classifier.classes,
        "best_model": m.get("best_model"),
        "candidates": m.get("candidates"),
        "train_rows": m.get("train_rows"),
        "test_rows": m.get("test_rows"),
        "class_counts": m.get("class_counts"),
    }


@router.get("/forecast/crimes", response_model=ForecastResponse, dependencies=[Depends(require_role(["admin"]))])
async def forecast_crimes(
    periods: int = Query(30, description="Number of periods to forecast"),
    frequency: str = Query('D', description="Forecast frequency: D (daily), W (weekly), M (monthly)"),
    location_id: Optional[int] = Query(None, description="Filter by location ID")
):
    """
    Forecast future crime trends using time series analysis
    
    Uses ARIMA model to predict crime counts for the next N periods
    
    """
    _require_ml()
    try:
        # Extract time series data
        extractor = CrimeDataExtractor(DB_URL)
        df_ts = extractor.get_time_series_data(
            frequency=frequency,
            location_id=location_id
        )
        
        if len(df_ts) < 30:
            raise HTTPException(
                status_code=400,
                detail="Insufficient data for forecasting (need at least 30 data points)"
            )
        
        # Initialize forecaster
        forecaster = CrimeTimeSeriesForecaster(model_type='arima')
        
        # Prepare time series
        ts = df_ts.set_index('date_occ')['crime_count']
        
        # Train model
        forecaster.train_arima(ts, auto_order=True)
        
        # Generate forecast
        forecast_df = forecaster.forecast(periods=periods, frequency=frequency)
        
        # Get trend analysis
        trend_analysis = forecaster.get_trend_analysis(forecast_df)
        
        extractor.close()
        
        # Format response
        forecast_data = [
            {
                'date': row['date'].strftime('%Y-%m-%d'),
                'forecast': float(row['forecast']),
                'lower_bound': float(row['lower_bound']),
                'upper_bound': float(row['upper_bound'])
            }
            for _, row in forecast_df.iterrows()
        ]
        
        response = {
            'forecast_period_days': periods,
            'forecast_data': forecast_data,
            'trend_analysis': trend_analysis,
            'total_predicted_crimes': int(forecast_df['forecast'].sum())
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {str(e)}")


@router.get("/analytics/summary", dependencies=[Depends(require_role(["admin"]))])
async def get_analytics_summary():
    """
    Get overall AI analytics summary
    
    Returns a comprehensive overview of all AI insights
    """
    _require_ml()
    _require_ml()
    try:
        extractor = CrimeDataExtractor(DB_URL)
        df_crimes = extractor.get_crime_cases_with_location()
        df_locations = extractor.get_location_crime_counts()
        df_ts = extractor.get_time_series_data(frequency='M')
        
        # Hotspot analysis
        predictor = CrimeHotspotPredictor()
        features = predictor.prepare_features(df_crimes, df_locations)
        predictor.train_risk_model(features)
        risk_scores = predictor.calculate_risk_scores(features)
        
        # Time series forecast
        forecaster = CrimeTimeSeriesForecaster(model_type='arima')
        ts = df_ts.set_index('date_occ')['crime_count']
        
        if len(ts) >= 30:
            forecaster.train_arima(ts, auto_order=False, order=(5, 1, 0))
            forecast_df = forecaster.forecast(periods=30, frequency='D')
            trend = forecaster.get_trend_analysis(forecast_df)
        else:
            trend = {'trend_category': 'Insufficient data'}
        
        extractor.close()
        
        # Compile summary
        summary = {
            'generated_at': datetime.now().isoformat(),
            'total_cases': len(df_crimes),
            'total_locations': len(df_locations),
            'high_risk_locations': len(risk_scores[risk_scores['risk_category'].isin(['High', 'Very High'])]),
            'top_3_hotspots': risk_scores.head(3)[['landmark', 'city', 'composite_risk_score']].to_dict('records'),
            'crime_trend': trend.get('trend_category', 'Unknown'),
            'predicted_crimes_next_month': int(trend.get('total_predicted_crimes', 0)) if 'total_predicted_crimes' in trend else 0
        }
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")


@router.get("/models/status", dependencies=[Depends(require_role(["admin"]))])
async def get_model_status():
    """
    Get status of all AI models
    
    Returns information about which models are trained and available
    """
    import os
    
    model_dir = "models"
    models_status = {
        'hotspot_predictor': os.path.exists(f"{model_dir}/hotspot/hotspot_models.pkl"),
        'matter_classifier': bool(MATTER_MODEL_PATH) and os.path.exists(MATTER_MODEL_PATH),
        'time_series_arima': os.path.exists(f"{model_dir}/forecasting/forecast_arima.pkl"),
    }
    
    return {
        'models': models_status,
        'all_models_ready': all(models_status.values()),
        'ready_count': sum(models_status.values()),
        'total_count': len(models_status),
        'ml_dependencies_installed': ML_AVAILABLE,
    }