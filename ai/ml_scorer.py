"""
ML Opportunity Scorer

Predicts execution success probability using Random Forest.
Trains on historical opportunities from PostgreSQL.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import os
from typing import Dict, Optional
from datetime import datetime


class OpportunityScorer:
    """ML model to score arbitrage opportunities"""
    
    def __init__(self, model_path='models/opportunity_scorer.pkl'):
        self.model_path = model_path
        self.scaler_path = 'models/scaler.pkl'
        self.model = None
        self.scaler = None
        self.is_trained = False
        
        # Load if exists
        if os.path.exists(model_path):
            self.load()
    
    def extract_features(self, opportunity: Dict) -> np.array:
        """
        Extract ML features from opportunity.
        
        Features:
        1. match_confidence - How well markets match
        2. net_profit - Profit after fees
        3. roi - Return on investment
        4. price_spread - Abs difference in YES prices
        5. kalshi_spread - Kalshi bid-ask spread
        6. poly_spread - Polymarket bid-ask spread
        7. hour_of_day - Time patterns
        8. day_of_week - Day patterns
        9. ai_score - FunctionGemma score (if available)
        10. sentiment_score - Market sentiment
        11. mispricing_likelihood - AI mispricing signal
        12. risk_score - AI risk assessment
        """
        # Parse prices
        k_prices = opportunity.get('kalshi_prices', 'YES: $0.5, NO: $0.5')
        p_prices = opportunity.get('polymarket_prices', 'YES: $0.5, NO: $0.5')
        
        k_yes, k_no = self._parse_prices(k_prices)
        p_yes, p_no = self._parse_prices(p_prices)
        
        # Time features
        timestamp = opportunity.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # AI features
        ai_analysis = opportunity.get('ai_analysis', {})
        sentiment = ai_analysis.get('sentiment', {}) if ai_analysis else {}
        mispricing = ai_analysis.get('mispricing', {}) if ai_analysis else {}
        risk = ai_analysis.get('risk', {}) if ai_analysis else {}
        
        features = [
            opportunity.get('match_confidence', 0.5),
            opportunity.get('net_profit', 0),
            opportunity.get('roi', 0),
            abs(k_yes - p_yes),  # price_spread
            abs(k_yes - k_no),   # kalshi_spread
            abs(p_yes - p_no),   # poly_spread
            timestamp.hour,
            timestamp.weekday(),
            opportunity.get('ai_score', 0.5),
            sentiment.get('sentiment_score', 0),
            mispricing.get('mispricing_likelihood', 0),
            risk.get('overall_risk', 0.5)
        ]
        
        return np.array(features).reshape(1, -1)
    
    def _parse_prices(self, price_str: str) -> tuple:
        """Parse 'YES: $0.45, NO: $0.55' into (0.45, 0.55)"""
        try:
            parts = price_str.split(',')
            yes = float(parts[0].split('$')[1])
            no = float(parts[1].split('$')[1])
            return yes, no
        except:
            return 0.5, 0.5
    
    def train_from_database(self, db_logger):
        """
        Train model from PostgreSQL data.
        
        Args:
            db_logger: OpportunityLogger instance
        """
        import psycopg2
        
        # Fetch training data
        conn = db_logger._get_connection()
        query = """
            SELECT * FROM opportunity_training_data
            WHERE ai_enabled = TRUE
            ORDER BY timestamp DESC
            LIMIT 1000
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if len(df) < 10:
            print(f"⚠️  Not enough training data ({len(df)} rows). Need at least 10.")
            return False
        
        # Prepare features
        feature_cols = [
            'match_confidence', 'net_profit', 'roi',
            'price_spread', 'kalshi_spread', 'poly_spread',
            'hour_of_day', 'day_of_week',
            'ai_score', 'sentiment_score', 
            'mispricing_likelihood', 'risk_score'
        ]
        
        X = df[feature_cols].fillna(0.5)
        y = df['executed'].fillna(0).astype(int)
        
        # Check class balance
        if y.sum() < 3:
            print("⚠️  Not enough positive examples (executed=True). Keep collecting data.")
            return False
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y if y.sum() > 5 else None
        )
        
        # Scale
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            class_weight='balanced'
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        print(f"✅ Model trained!")
        print(f"   Training accuracy: {train_score:.3f}")
        print(f"   Test accuracy: {test_score:.3f}")
        print(f"   Training samples: {len(X_train)}")
        
        # Feature importance
        importances = self.model.feature_importances_
        for i, col in enumerate(feature_cols):
            if importances[i] > 0.05:
                print(f"   {col}: {importances[i]:.3f}")
        
        self.is_trained = True
        self.save()
        
        return True
    
    def train_from_mock_data(self, n_samples=100):
        """
        Train from synthetic data (for testing when no real data).
        """
        print("⚠️  Training from mock data (for testing only)")
        
        # Generate synthetic opportunities
        np.random.seed(42)
        
        # Good opportunities (high profit, low risk)
        good_opps = np.random.normal([0.8, 0.10, 2.0, 0.15, 0.05, 0.05, 14, 2, 0.75, 0.6, 0.6, 0.2], 
                                     [0.1, 0.05, 1.0, 0.05, 0.02, 0.02, 4, 2, 0.1, 0.2, 0.2, 0.1],
                                     (n_samples//2, 12))
        
        # Bad opportunities (low profit, high risk)
        bad_opps = np.random.normal([0.6, 0.02, 0.5, 0.05, 0.15, 0.15, 10, 4, 0.3, 0.2, 0.2, 0.7],
                                    [0.15, 0.01, 0.3, 0.03, 0.05, 0.05, 5, 2, 0.15, 0.2, 0.2, 0.15],
                                    (n_samples//2, 12))
        
        X = np.vstack([good_opps, bad_opps])
        y = np.array([1] * (n_samples//2) + [0] * (n_samples//2))
        
        # Shuffle
        idx = np.random.permutation(len(X))
        X, y = X[idx], y[idx]
        
        # Scale
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        
        self.model.fit(X_scaled, y)
        
        print(f"✅ Mock model trained (accuracy: {self.model.score(X_scaled, y):.3f})")
        self.is_trained = True
        self.save()
    
    def score_opportunity(self, opportunity: Dict) -> Dict:
        """
        Score an opportunity (0.0 to 1.0).
        
        Returns:
            {
                "ml_score": float,           # 0-1 probability of success
                "ml_recommendation": str,    # EXECUTE/CONSIDER/SKIP
                "confidence": float,         # Model confidence
                "features": dict            # Feature values used
            }
        """
        if not self.is_trained:
            return {
                "ml_score": 0.5,
                "ml_recommendation": "UNTRAINED",
                "confidence": 0.0,
                "features": {}
            }
        
        # Extract features
        features = self.extract_features(opportunity)
        features_scaled = self.scaler.transform(features)
        
        # Predict
        probability = self.model.predict_proba(features_scaled)[0][1]  # Prob of success
        confidence = max(self.model.predict_proba(features_scaled)[0])  # Max class prob
        
        # Recommendation
        if probability >= 0.7 and confidence >= 0.75:
            recommendation = "EXECUTE - High ML confidence"
        elif probability >= 0.5 and confidence >= 0.6:
            recommendation = "CONSIDER - Moderate ML confidence"
        else:
            recommendation = "SKIP - Low ML confidence"
        
        return {
            "ml_score": float(probability),
            "ml_recommendation": recommendation,
            "confidence": float(confidence),
            "features": {
                "match_confidence": float(features[0][0]),
                "net_profit": float(features[0][1]),
                "roi": float(features[0][2]),
                "price_spread": float(features[0][3])
            }
        }
    
    def save(self):
        """Save model and scaler"""
        os.makedirs('models', exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        print(f"✅ Model saved to {self.model_path}")
    
    def load(self):
        """Load model and scaler"""
        if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            self.is_trained = True
            print(f"✅ Model loaded from {self.model_path}")
            return True
        return False


# Quick test
if __name__ == "__main__":
    scorer = OpportunityScorer()
    
    # Train with mock data
    scorer.train_from_mock_data(n_samples=200)
    
    # Test scoring
    test_opp = {
        'match_confidence': 0.85,
        'net_profit': 0.12,
        'roi': 2.5,
        'kalshi_prices': 'YES: $0.45, NO: $0.55',
        'polymarket_prices': 'YES: $0.42, NO: $0.58',
        'ai_score': 0.75,
        'timestamp': datetime.now(),
        'ai_analysis': {
            'sentiment': {'sentiment_score': 0.6},
            'mispricing': {'mispricing_likelihood': 0.65},
            'risk': {'overall_risk': 0.25}
        }
    }
    
    result = scorer.score_opportunity(test_opp)
    print(f"\n📊 ML Scoring Result:")
    print(f"   ML Score: {result['ml_score']:.3f}")
    print(f"   Recommendation: {result['ml_recommendation']}")
    print(f"   Confidence: {result['confidence']:.3f}")
