"""
Comprehensive Training Script for All AI Models
Trains hotspot predictor, crime classifier, and time series forecaster

USAGE:
    python train_models.py --db-url "postgresql+psycopg://user:pass@localhost/db"
    
Run from: backend/ directory
"""
import sys
import os
from datetime import datetime
import json

# Fix import paths - add the backend directory to Python path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

# Now we can import from app.ai_models
from app.ai_models.matter_classifier import MatterTypeClassifier, DEFAULT_DATA

# The locality and forecasting models need the database and extra packages
# (statsmodels, prophet). The matter classifier needs neither.
try:
    from app.ai_models.data_extractor import CrimeDataExtractor
    from app.ai_models.hotspot_predictor import CrimeHotspotPredictor
    from app.ai_models.time_series_forecaster import CrimeTimeSeriesForecaster
except ImportError as e:
    CrimeDataExtractor = CrimeHotspotPredictor = CrimeTimeSeriesForecaster = None
    DB_MODELS_IMPORT_ERROR = e


def train_matter_classifier(data_path: str = DEFAULT_DATA) -> dict:
    """Train the five-class matter-type text classifier from ml_data/matter_types.csv."""
    print("\n" + "="*70)
    print("TRAINING MATTER TYPE CLASSIFIER")
    print("="*70)
    print(f"Data: {data_path}\n")
    clf = MatterTypeClassifier()
    metrics = clf.train(data_path)
    path = clf.save()
    print(f"✓ Saved to {path}")
    best = metrics["candidates"][metrics["best_model"]]
    return {"status": "success", "best_model": metrics["best_model"], **best,
            "candidates": metrics["candidates"], "model_path": path}


class AIModelTrainer:
    """Trains and saves all AI models"""
    
    def __init__(self, db_url: str):
        """
        Initialize the trainer
        
        Args:
            db_url: PostgreSQL connection string
        """
        self.db_url = db_url
        self.extractor = CrimeDataExtractor(db_url)
        self.results = {}
        
    def create_model_directories(self):
        """Create necessary directories for saving models"""
        directories = [
            'models',
            'models/hotspot',
            'models/classifier',
            'models/forecasting'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"✓ Directory created: {directory}")
    
    def train_hotspot_predictor(self):
        """Train crime hotspot prediction model"""
        print("\n" + "="*70)
        print("TRAINING CRIME HOTSPOT PREDICTOR")
        print("="*70)
        
        try:
            # Extract data
            print("\n1. Extracting crime and location data...")
            df_crimes = self.extractor.get_crime_cases_with_location()
            df_locations = self.extractor.get_location_crime_counts()
            print(f"   ✓ Total crimes: {len(df_crimes)}")
            print(f"   ✓ Total locations: {len(df_locations)}")
            
            # Initialize predictor
            print("\n2. Initializing hotspot predictor...")
            predictor = CrimeHotspotPredictor(model_dir='models/hotspot')
            
            # Prepare features
            print("\n3. Preparing features...")
            features = predictor.prepare_features(df_crimes, df_locations)
            print(f"   ✓ Features prepared: {len(features)} locations")
            
            # Train risk model
            print("\n4. Training risk prediction model...")
            predictor.train_risk_model(features)
            
            # Spatial clustering
            print("\n5. Performing spatial clustering...")
            predictor.perform_spatial_clustering(features)
            
            # Calculate risk scores
            print("\n6. Calculating risk scores...")
            risk_scores = predictor.calculate_risk_scores(features)
            print(f"   ✓ Top hotspot: {risk_scores.iloc[0]['landmark']} (Risk: {risk_scores.iloc[0]['composite_risk_score']:.2f})")
            
            # Predict trends
            print("\n7. Predicting trends...")
            trends = predictor.predict_hotspot_trends(features, days_ahead=30)
            
            # Generate report
            report = predictor.generate_hotspot_report(risk_scores, trends)
            
            # Save model
            print("\n8. Saving model...")
            predictor.save_models('models/hotspot/hotspot_models.pkl')
            
            self.results['hotspot_predictor'] = {
                'status': 'success',
                'locations_analyzed': len(features),
                'high_risk_locations': report['high_risk_locations'],
                'model_path': 'models/hotspot/hotspot_models.pkl'
            }
            
            print("\n✓ Hotspot predictor trained successfully!")
            
        except Exception as e:
            print(f"\n✗ Hotspot predictor training failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.results['hotspot_predictor'] = {
                'status': 'failed',
                'error': str(e)
            }
    
    def train_crime_classifier(self):
        """Train the matter-type classifier (does not use the database)."""
        try:
            self.results['matter_classifier'] = train_matter_classifier()
        except Exception as e:
            print(f"\n✗ Matter classifier training failed: {str(e)}")
            self.results['matter_classifier'] = {'status': 'failed', 'error': str(e)}

    def train_time_series_forecaster(self):
        """Train time series forecasting model"""
        print("\n" + "="*70)
        print("TRAINING TIME SERIES FORECASTER")
        print("="*70)
        
        try:
            # Extract time series data
            print("\n1. Extracting time series data...")
            df_ts = self.extractor.get_time_series_data(frequency='D')
            print(f"   ✓ Time series length: {len(df_ts)} days")
            
            if len(df_ts) < 30:
                print("   ⚠ Warning: Insufficient data for time series (< 30 days)")
                self.results['forecaster'] = {
                    'status': 'skipped',
                    'reason': 'Insufficient data'
                }
                return
            
            # Initialize forecaster
            print("\n2. Initializing ARIMA forecaster...")
            forecaster = CrimeTimeSeriesForecaster(
                model_type='arima',
                model_dir='models/forecasting'
            )
            
            # Prepare time series
            ts = df_ts.set_index('date_occ')['crime_count']
            
            # Analyze seasonality
            print("\n3. Analyzing seasonality...")
            seasonality = forecaster.analyze_seasonality(ts, period=7)
            print(f"   ✓ Trend strength: {seasonality.get('trend_strength', 0):.4f}")
            print(f"   ✓ Seasonal strength: {seasonality.get('seasonal_strength', 0):.4f}")
            
            # Train model
            print("\n4. Training ARIMA model...")
            forecaster.train_arima(ts, auto_order=True)
            
            # Evaluate
            print("\n5. Evaluating model...")
            if len(ts) >= 60:
                metrics = forecaster.evaluate_model(ts, test_size=30)
            else:
                metrics = {'note': 'Insufficient data for evaluation'}
            
            # Generate forecast
            print("\n6. Generating 30-day forecast...")
            forecast_df = forecaster.forecast(periods=30, frequency='D')
            trend = forecaster.get_trend_analysis(forecast_df)
            print(f"   ✓ Trend: {trend['trend_category']}")
            print(f"   ✓ Predicted crimes (next 30 days): {trend['total_predicted_crimes']}")
            
            # Save model
            print("\n7. Saving model...")
            forecaster.save_model('models/forecasting/forecast_arima.pkl')
            
            self.results['forecaster'] = {
                'status': 'success',
                'trend': trend['trend_category'],
                'predicted_crimes_30d': trend['total_predicted_crimes'],
                'model_path': 'models/forecasting/forecast_arima.pkl'
            }
            
            print("\n✓ Time series forecaster trained successfully!")
            
        except Exception as e:
            print(f"\n✗ Time series forecaster training failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.results['forecaster'] = {
                'status': 'failed',
                'error': str(e)
            }
    
    def train_all_models(self):
        """Train all AI models sequentially"""
        print("\n" + "="*70)
        print("AI MODEL TRAINING PIPELINE")
        print("="*70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Database: {self.db_url}")
        
        # Create directories
        print("\nCreating model directories...")
        self.create_model_directories()
        
        # Train all models
        self.train_hotspot_predictor()
        self.train_crime_classifier()
        self.train_time_series_forecaster()
        
        # Save training results
        results_file = f"training_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Print summary
        print("\n" + "="*70)
        print("TRAINING SUMMARY")
        print("="*70)
        
        for model_name, result in self.results.items():
            status_icon = "✓" if result['status'] == 'success' else "✗"
            print(f"{status_icon} {model_name}: {result['status']}")
            if result['status'] == 'success':
                for key, value in result.items():
                    if key not in ['status', 'model_path']:
                        print(f"     {key}: {value}")
        
        print(f"\nResults saved to: {results_file}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
    
    def close(self):
        """Close database connection"""
        self.extractor.close()


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Train the matter-type, locality, and intake models')
    parser.add_argument(
        '--db-url',
        type=str,
        default=os.getenv('DATABASE_URL', 'postgresql+psycopg://postgres:your_password@localhost:5432/law_firm_db'),
        help='PostgreSQL database URL'
    )
    parser.add_argument(
        '--model',
        type=str,
        choices=['all', 'hotspot', 'classifier', 'forecaster'],
        default='all',
        help='Which model to train'
    )
    
    args = parser.parse_args()
    
    # Check if running from correct directory
    if not os.path.exists('app'):
        print("\n" + "="*70)
        print("ERROR: Please run this script from the 'backend' directory!")
        print("="*70)
        print("\nCurrent directory:", os.getcwd())
        print("\nCorrect usage:")
        print("  cd backend")
        print("  python train_models.py --db-url 'your_db_url'")
        print("\n" + "="*70)
        sys.exit(1)
    
    # The classifier trains from a CSV, so it needs no database connection.
    if args.model == 'classifier':
        train_matter_classifier()
        sys.exit(0)

    if CrimeDataExtractor is None:
        print(f"Locality/forecast models need requirements-ml.txt installed: {DB_MODELS_IMPORT_ERROR}")
        sys.exit(1)

    # Initialize trainer
    trainer = AIModelTrainer(args.db_url)
    
    try:
        if args.model == 'all':
            trainer.train_all_models()
        elif args.model == 'hotspot':
            trainer.create_model_directories()
            trainer.train_hotspot_predictor()
        elif args.model == 'classifier':
            trainer.create_model_directories()
            trainer.train_crime_classifier()
        elif args.model == 'forecaster':
            trainer.create_model_directories()
            trainer.train_time_series_forecaster()
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        trainer.close()