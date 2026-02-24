import joblib
import pandas as pd


try:
    model = joblib.load("ml_model.pkl")
    print("[MODEL] Loaded successfully ✅")
except Exception as e:
    print(f"[ERROR] Could not load ML model: {e}")
    model = None




def predict_plan_score(plan_row: dict, user_profile: dict) -> float:


    if model is None:
        print("[WARN] ML model not available. Score = 0")
        return 0.0

    try:
        # Build single-row dataframe
        data = {
            "age_value": user_profile.get("age", 30),
            "premium": plan_row.get("premium", 0),
            "ehb_percent": plan_row.get("ehb_percent", 0),
            "avg_copay": plan_row.get("avg_copay", 0),
            "avg_coinsurance": plan_row.get("avg_coinsurance", 0),

            # engineered values
            "premium_per_person": plan_row.get("premium", 0),
            "coverage_score": plan_row.get("ehb_percent", 0) / max(plan_row.get("premium", 1), 1),
            "total_dental": plan_row.get("adult_dental", 0) + plan_row.get("child_dental", 0),

            # categorical
            "family_type": user_profile.get("family_type", "Individual"),
            "plan_type": plan_row.get("plan_type", "PPO"),
            "meta_level": plan_row.get("meta_level", "Silver"),
            "state_code": plan_row.get("state_code", "AL"),
            "rating_area": plan_row.get("rating_area", "Rating Area 1"),
        }

        df = pd.DataFrame([data])

        # Directly predict using pipeline
        score = float(model.predict(df)[0])
        return score

    except Exception as e:
        print("[ERROR] Prediction failed:", e)
        return 0.0
