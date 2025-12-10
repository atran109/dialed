"""
Model evaluation and feature importance analysis.

Shows which features are most important for detecting distraction.

USAGE:
  python models/evaluate.py
"""

import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc


def load_model_and_config():
    """Load trained model and feature configuration."""
    print("📂 Loading model and config...")

    model = joblib.load("models/model.pkl")
    with open("models/feature_config.json", 'r') as f:
        config = json.load(f)

    print(f"  ✓ Model loaded")
    print(f"  ✓ Features: {config['num_features']}")
    print(f"  ✓ Trained ROC-AUC: {config['metrics']['roc_auc']:.3f}")

    return model, config


def analyze_feature_importance(model, feature_names):
    """
    Analyze and display feature importance.

    Shows which features contribute most to predictions.
    """
    print(f"\n📊 Feature Importance Analysis\n")

    # Get feature importance from LightGBM
    importance = model.feature_importances_

    # Create DataFrame
    feature_importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importance
    }).sort_values('importance', ascending=False)

    # Display top 15 features
    print("Top 15 most important features:")
    for idx, row in feature_importance_df.head(15).iterrows():
        bar = "█" * int(row['importance'] / feature_importance_df['importance'].max() * 50)
        print(f"  {row['feature']:30s} {bar} {row['importance']:.1f}")

    # Save to CSV
    feature_importance_df.to_csv("models/feature_importance.csv", index=False)
    print(f"\n  ✓ Saved to models/feature_importance.csv")

    return feature_importance_df


def plot_feature_importance(feature_importance_df):
    """Create bar plot of top 10 features."""
    print(f"\n📈 Creating feature importance plot...")

    top_10 = feature_importance_df.head(10)

    plt.figure(figsize=(10, 6))
    plt.barh(range(len(top_10)), top_10['importance'])
    plt.yticks(range(len(top_10)), top_10['feature'])
    plt.xlabel('Importance')
    plt.title('Top 10 Most Important Features for Distraction Detection')
    plt.gca().invert_yaxis()
    plt.tight_layout()

    plt.savefig('models/feature_importance.png', dpi=150)
    print(f"  ✓ Plot saved to models/feature_importance.png")
    plt.close()


def main():
    """
    Main evaluation function.

    Loads model and analyzes feature importance.
    """
    print("=" * 60)
    print("DIALED - Model Evaluation")
    print("=" * 60)
    print()

    try:
        # Load model
        model, config = load_model_and_config()

        # Analyze feature importance
        feature_importance_df = analyze_feature_importance(model, config['feature_names'])

        # Create plot
        plot_feature_importance(feature_importance_df)

        # Summary
        print(f"\n✅ Evaluation complete!")
        print(f"\n🎯 Key Insights:")

        top_feature = feature_importance_df.iloc[0]
        print(f"  - Most important feature: {top_feature['feature']}")

        # Categorize features
        gaze_features = feature_importance_df[
            ~feature_importance_df['feature'].str.contains('domain|tab|keypress|idle')
        ]
        browser_features = feature_importance_df[
            feature_importance_df['feature'].str.contains('domain|tab|keypress|idle')
        ]

        avg_gaze_importance = gaze_features['importance'].mean()
        avg_browser_importance = browser_features['importance'].mean()

        print(f"  - Avg gaze feature importance: {avg_gaze_importance:.1f}")
        print(f"  - Avg browser feature importance: {avg_browser_importance:.1f}")

        if avg_gaze_importance > avg_browser_importance:
            print(f"  - Gaze features are more predictive (physical behavior)")
        else:
            print(f"  - Browser features are more predictive (digital behavior)")

        print(f"\n📊 Current Performance:")
        print(f"  - ROC-AUC: {config['metrics']['roc_auc']:.3f}")
        print(f"  - F1 Score: {config['metrics']['f1_score']:.3f}")

    except FileNotFoundError as e:
        print(f"\n❌ Error: Model not found!")
        print(f"   Run this first: python models/train.py")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
