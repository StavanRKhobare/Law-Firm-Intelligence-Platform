"""
Crime Hotspot Prediction Model
Uses clustering, spatial analysis, and risk scoring to identify high-crime areas
"""
import os
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
import joblib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


# recent_crimes_30d is the risk model's target and recency_score is derived
# from it, so neither is an input; otherwise the model just copies its input.
RISK_FEATURES = [
    'total_crimes', 'crime_frequency',
    'crime_type_diversity', 'open_cases', 'total_evidence',
    'total_suspects', 'total_victims', 'density_score',
    'open_case_ratio', 'evidence_ratio',
]


class CrimeHotspotPredictor:
    """
    Predicts crime hotspots using:
    1. Historical crime density
    2. Temporal patterns
    3. Spatial clustering (DBSCAN)
    4. Risk scoring
    """
    
    def __init__(self, model_dir: str = "models/hotspot"):
        self.model_dir = model_dir
        self.risk_scaler = StandardScaler()
        self.cluster_scaler = StandardScaler()
        self.risk_model = None
        self.cluster_model = None
        self.location_features = None

        
    def prepare_features(self, df_crimes: pd.DataFrame, df_locations: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for hotspot prediction
        
        Args:
            df_crimes: DataFrame with crime cases
            df_locations: DataFrame with location statistics
            
        Returns:
            DataFrame with engineered features
        """
        # Aggregate crime statistics by location
        location_stats = df_crimes.groupby('location_id').agg({
            'crime_case_id': 'count',
            'date_occ': ['min', 'max'],
            'status': lambda x: (x == 'Filed').sum(),
            'evidence_count': 'sum',
            'suspect_count': 'sum',
            'victim_count': 'sum'
        }).reset_index()
        
        location_stats.columns = [
            'location_id', 'total_crimes', 'first_crime', 'last_crime',
            'open_cases', 'total_evidence', 'total_suspects', 'total_victims'
        ]
        
        # Calculate temporal features
        location_stats['days_active'] = (
            pd.to_datetime(location_stats['last_crime']) - 
            pd.to_datetime(location_stats['first_crime'])
        ).dt.days
        location_stats['crime_frequency'] = location_stats['total_crimes'] / (location_stats['days_active'] + 1)
        
        # Recent crime trend (last 30 days)
        recent_date = df_crimes['date_occ'].max() - timedelta(days=30)
        recent_crimes = df_crimes[df_crimes['date_occ'] >= recent_date]
        recent_counts = recent_crimes.groupby('location_id').size().reset_index(name='recent_crimes_30d')
        
        location_stats = location_stats.merge(recent_counts, on='location_id', how='left')
        location_stats['recent_crimes_30d'] = location_stats['recent_crimes_30d'].fillna(0)
        
        # Crime type diversity
        crime_type_diversity = df_crimes.groupby('location_id')['crime_types'].apply(
            lambda x: len(set('|'.join(x.dropna()).split('|')))
        ).reset_index(name='crime_type_diversity')
        
        location_stats = location_stats.merge(crime_type_diversity, on='location_id', how='left')
        
        # Merge location_stats with location data (location_stats has the crime counts)
        features = location_stats.merge(
            df_locations[['location_id', 'landmark', 'pincode', 'city', 'district', 'state']], 
            on='location_id', 
            how='left'
        )
        features = features.fillna(0)
        
        # Calculate risk score components
        features['density_score'] = features['total_crimes'] / (features['days_active'] + 1)
        features['recency_score'] = features['recent_crimes_30d'] / (features['total_crimes'] + 1)
        features['open_case_ratio'] = features['open_cases'] / (features['total_crimes'] + 1)
        features['evidence_ratio'] = features['total_evidence'] / (features['total_crimes'] + 1)
        
        self.location_features = features
        return features
    
    def train_risk_model(self, features: pd.DataFrame, target_col: str = 'recent_crimes_30d'):
        """
        Train a model to predict crime risk
        
        Args:
            features: DataFrame with location features
            target_col: Column to predict (default: recent crimes)
        """
        # Select feature columns
        feature_cols = RISK_FEATURES
        
        X = features[feature_cols].values
        y = features[target_col].values
        
        # Scale features
        
        X_scaled = self.risk_scaler.fit_transform(X)

        
        # Train Random Forest for risk prediction
        self.risk_model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.risk_model.fit(X_scaled, y)
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': self.risk_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("Feature Importance:")
        print(feature_importance)
        
        return self.risk_model
    
    def perform_spatial_clustering(self, features: pd.DataFrame, eps: float = 0.5, min_samples: int = 2):
        """
        Perform spatial clustering to identify hotspot zones
        
        Args:
            features: DataFrame with location features
            eps: DBSCAN epsilon parameter
            min_samples: Minimum samples for a cluster
            
        Returns:
            Cluster labels
        """
        # Use crime statistics for clustering
        cluster_features = features[[
            'total_crimes', 'crime_frequency', 'recent_crimes_30d',
            'crime_type_diversity', 'density_score'
        ]].values
        
        # Scale features
        
        cluster_scaled = self.cluster_scaler.fit_transform(cluster_features)

        
        # DBSCAN clustering
        self.cluster_model = DBSCAN(eps=eps, min_samples=min_samples)
        cluster_labels = self.cluster_model.fit_predict(cluster_scaled)
        
        features['cluster'] = cluster_labels
        
        # Analyze clusters
        cluster_stats = features.groupby('cluster').agg({
            'total_crimes': ['mean', 'sum'],
            'recent_crimes_30d': ['mean', 'sum'],
            'crime_frequency': 'mean',
            'location_id': 'count'
        }).round(2)
        
        print("\nCluster Statistics:")
        print(cluster_stats)
        
        return cluster_labels
    
    def calculate_risk_scores(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate comprehensive risk scores for each location
        
        Args:
            features: DataFrame with location features
            
        Returns:
            DataFrame with risk scores
        """
        # Normalize each component to 0-100 scale
        def normalize_score(series):
            if series.max() == 0:
                return series
            return (series / series.max()) * 100
        
        risk_scores = pd.DataFrame()
        risk_scores['location_id'] = features['location_id']
        risk_scores['landmark'] = features['landmark']
        risk_scores['city'] = features['city']
        risk_scores['district'] = features['district']
        
        # Individual risk components
        risk_scores['historical_risk'] = normalize_score(features['total_crimes'])
        risk_scores['recent_activity_risk'] = normalize_score(features['recent_crimes_30d'])
        risk_scores['frequency_risk'] = normalize_score(features['crime_frequency'])
        risk_scores['diversity_risk'] = normalize_score(features['crime_type_diversity'])
        risk_scores['open_case_risk'] = normalize_score(features['open_cases'])
        
        # Weighted composite risk score
        weights = {
            'recent_activity_risk': 0.35,  # Recent crimes are most important
            'frequency_risk': 0.25,        # How often crimes occur
            'historical_risk': 0.20,       # Total crime history
            'diversity_risk': 0.10,        # Variety of crimes
            'open_case_risk': 0.10         # Unresolved cases
        }
        
        risk_scores['composite_risk_score'] = sum(
            risk_scores[col] * weight for col, weight in weights.items()
        )
        
        # Risk categories
        risk_scores['risk_category'] = pd.cut(
            risk_scores['composite_risk_score'],
            bins=[0, 20, 40, 60, 80, 100],
            labels=['Very Low', 'Low', 'Medium', 'High', 'Very High']
        )
        
        # Add prediction from ML model if trained
        if self.risk_model is not None:
            feature_cols = RISK_FEATURES
            X = features[feature_cols].values
            X_scaled = self.risk_scaler.transform(X)
            risk_scores['predicted_future_crimes'] = self.risk_model.predict(X_scaled)
        
        # Sort by risk
        risk_scores = risk_scores.sort_values('composite_risk_score', ascending=False)
        
        return risk_scores
    
    def identify_top_hotspots(self, risk_scores: pd.DataFrame, top_n: int = 10) -> List[Dict]:
        """
        Identify top N crime hotspots
        
        Args:
            risk_scores: DataFrame with risk scores
            top_n: Number of top hotspots to return
            
        Returns:
            List of hotspot dictionaries
        """
        top_hotspots = risk_scores.head(top_n)
        
        hotspot_list = []
        for _, row in top_hotspots.iterrows():
            hotspot = {
                'location_id': int(row['location_id']),
                'landmark': row['landmark'],
                'city': row['city'],
                'district': row['district'],
                'risk_score': round(float(row['composite_risk_score']), 2),
                'risk_category': str(row['risk_category']),
                'historical_crimes': int(row['historical_risk']) if 'historical_risk' in row else 0,
                'recent_crimes': int(row['recent_activity_risk']) if 'recent_activity_risk' in row else 0,
                'predicted_future_crimes': round(float(row['predicted_future_crimes']), 2) if 'predicted_future_crimes' in row else 0
            }
            hotspot_list.append(hotspot)
        
        return hotspot_list
    
    def predict_hotspot_trends(self, features: pd.DataFrame, days_ahead: int = 30) -> pd.DataFrame:
        """
        Predict crime trends for each location
        
        Args:
            features: DataFrame with location features
            days_ahead: Number of days to predict ahead
            
        Returns:
            DataFrame with predictions
        """
        if self.risk_model is None:
            raise ValueError("Risk model not trained. Call train_risk_model() first.")
        
        feature_cols = RISK_FEATURES
        
        X = features[feature_cols].values
        X_scaled = self.risk_scaler.transform(X)

        
        predictions = self.risk_model.predict(X_scaled)
        
        # Scale predictions based on forecast horizon
        scaling_factor = days_ahead / 30  # Model trained on 30-day data
        predictions_scaled = predictions * scaling_factor
        
        trends = pd.DataFrame({
            'location_id': features['location_id'],
            'landmark': features['landmark'],
            'city': features['city'],
            'current_monthly_avg': features['recent_crimes_30d'],
            'predicted_crimes_next_period': np.round(predictions_scaled, 2),
            'trend': np.where(
                predictions_scaled > features['recent_crimes_30d'] * 1.2,
                'Increasing',
                np.where(
                    predictions_scaled < features['recent_crimes_30d'] * 0.8,
                    'Decreasing',
                    'Stable'
                )
            )
        })
        
        return trends.sort_values('predicted_crimes_next_period', ascending=False)
    
    def save_models(self, filepath: str = None):
        """Save trained models to disk"""
        if filepath is None:
            filepath = f"{self.model_dir}/hotspot_models.pkl"
        models = {
            'risk_model': self.risk_model,
            'cluster_model': self.cluster_model,
            'risk_scaler': self.risk_scaler,
            'cluster_scaler': self.cluster_scaler,
            'location_features': self.location_features
        }

        
        joblib.dump(models, filepath)
        print(f"Models saved to {filepath}")
    
    def load_models(self, filepath: str = None):
        """Load trained models from disk"""
        if filepath is None:
            filepath = f"{self.model_dir}/hotspot_models.pkl"
        
        models = joblib.load(filepath)
        self.risk_model = models['risk_model']
        self.cluster_model = models['cluster_model']
        self.risk_scaler = models['risk_scaler']
        self.cluster_scaler = models['cluster_scaler']
        self.location_features = models['location_features']
        
        print(f"Models loaded from {filepath}")
    
    def generate_hotspot_report(self, risk_scores: pd.DataFrame, 
                                trends: pd.DataFrame) -> Dict:
        """
        Generate comprehensive hotspot analysis report
        
        Args:
            risk_scores: DataFrame with risk scores
            trends: DataFrame with trend predictions
            
        Returns:
            Dictionary with report data
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_locations_analyzed': len(risk_scores),
            'high_risk_locations': len(risk_scores[risk_scores['risk_category'].isin(['High', 'Very High'])]),
            'top_hotspots': self.identify_top_hotspots(risk_scores, top_n=10),
            'risk_distribution': risk_scores['risk_category'].value_counts().to_dict(),
            'trending_up_locations': len(trends[trends['trend'] == 'Increasing']),
            'trending_down_locations': len(trends[trends['trend'] == 'Decreasing']),
            'stable_locations': len(trends[trends['trend'] == 'Stable']),
            'avg_risk_score': float(risk_scores['composite_risk_score'].mean()),
            'max_risk_score': float(risk_scores['composite_risk_score'].max()),
        }
        
        return report


# Example usage
if __name__ == "__main__":
    from data_extractor import CrimeDataExtractor
    
    # Database connection
    DB_URL = os.environ["DATABASE_URL"]
    
    # Extract data
    extractor = CrimeDataExtractor(DB_URL)
    df_crimes = extractor.get_crime_cases_with_location()
    df_locations = extractor.get_location_crime_counts()
    
    # Initialize predictor
    predictor = CrimeHotspotPredictor()
    
    # Prepare features
    print("Preparing features...")
    features = predictor.prepare_features(df_crimes, df_locations)
    
    # Train risk model
    print("\nTraining risk prediction model...")
    predictor.train_risk_model(features)
    
    # Spatial clustering
    print("\nPerforming spatial clustering...")
    predictor.perform_spatial_clustering(features)
    
    # Calculate risk scores
    print("\nCalculating risk scores...")
    risk_scores = predictor.calculate_risk_scores(features)
    
    # Predict trends
    print("\nPredicting trends...")
    trends = predictor.predict_hotspot_trends(features, days_ahead=30)
    
    # Generate report
    print("\nGenerating hotspot report...")
    report = predictor.generate_hotspot_report(risk_scores, trends)
    
    print("\n=== HOTSPOT ANALYSIS REPORT ===")
    print(json.dumps(report, indent=2))
    
    # Save models
    predictor.save_models()
    
    extractor.close()