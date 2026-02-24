import pandas as pd
import joblib
import re
from sqlalchemy import create_engine
import urllib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error
from lightgbm import LGBMRegressor



try:
    print("[INFO] Connecting to SQL Server...")

    params = urllib.parse.quote_plus(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=LAPTOP-6MNJPHEQ;"
        "DATABASE=Medsurance;"
        "Trusted_Connection=yes;"
        "Encrypt=no;"
    )

    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    print("[INFO] Connection successful ✅")

except Exception as e:
    print(f"[ERROR] Database connection failed: {e}")
    exit(1)


def extract_age_value(age_group):
    if not isinstance(age_group, str):
        return float(age_group) if age_group else 0

    age_group = age_group.strip().replace("–", "-")

    if "-" in age_group:
        parts = age_group.split("-")
        try:
            return (float(parts[0]) + float(parts[1])) / 2
        except:
            return 0

    # handle text like "about 40" or "age 44"
    digits = re.findall(r"\d+", age_group)
    if digits:
        return float(digits[0])

    return 0


def extract_num_dependents(family_type):
    """Extract dependent count from text like 'Individual+3 or more children'."""
    if not isinstance(family_type, str):
        return 0
    match = re.search(r"(\d+)", family_type)
    if match:
        return int(match.group(1))
    elif "3 or more" in family_type:
        return 3
    return 0



query = """
SELECT 
    p.plan_id,
    p.plan_name,
    p.issuer_name,
    p.meta_level,
    p.plan_type,
    p.adult_dental,
    p.child_dental,
    l.state_code,
    l.rating_area,
    pp.age_group,
    pp.family_type,
    pp.premium,
    pp.ehb_percent,
    ISNULL(csr_avg.avg_copay, 0) AS avg_copay,
    ISNULL(csr_avg.avg_coinsurance, 0) AS avg_coinsurance
FROM Plans p
JOIN PlanPremiums pp ON p.plan_id = pp.plan_id
LEFT JOIN Locations l ON p.county_code = l.county_code
LEFT JOIN (
    SELECT 
        plan_id,
        AVG(CASE WHEN cost_type='Copay' THEN value END) AS avg_copay,
        AVG(CASE WHEN cost_type='Coinsurance' THEN value END) AS avg_coinsurance
    FROM PlanCSR
    WHERE csr_variant='Standard'
    GROUP BY plan_id
) AS csr_avg ON p.plan_id = csr_avg.plan_id
"""

print("[INFO] Loading data...")
df = pd.read_sql(query, engine)
print(f"[INFO] Loaded {len(df)} rows.")


print("[INFO] Normalizing family_type formatting...")

df["family_type"] = (
    df["family_type"]
    .astype(str)
    .str.replace(" + ", "+", regex=False)
    .str.replace("  ", " ")
    .str.strip()
)

print("[INFO] Normalizing rating_area formatting...")
df["rating_area"] = (
    df["rating_area"]
    .astype(str)
    .str.replace("  ", " ")
    .str.strip()
)

print("[INFO] Normalizing age values...")
df["age_value"] = df["age_group"].apply(extract_age_value)


print("[INFO] Feature engineering...")

df["dependents"] = df["family_type"].apply(extract_num_dependents)
df["premium_per_person"] = df["premium"] / (df["dependents"] + 1)
df["coverage_score"] = df["ehb_percent"] / df["premium"].replace(0, 1)
df["total_dental"] = df["adult_dental"].fillna(0) + df["child_dental"].fillna(0)

# synthetic target variable
df["value_score"] = (
    0.4 * (1 / (df["premium"] + 1)) +
    0.2 * (df["ehb_percent"] / 100) +
    0.2 * (1 / (df["avg_copay"] + 1)) +
    0.1 * (1 / (df["avg_coinsurance"] + 1)) +
    0.1 * df["total_dental"]
) * 1000

df = df.fillna(0)

print(f"[INFO] Final dataset dimensions: {df.shape}")



numeric_features = [
    "age_value", "premium", "ehb_percent", "avg_copay", "avg_coinsurance",
    "premium_per_person", "coverage_score", "total_dental"
]

categorical_features = ["family_type", "plan_type", "meta_level", "state_code", "rating_area"]

X = df[numeric_features + categorical_features]
y = df["value_score"]


print("[INFO] Building ML pipeline...")

preprocessor = ColumnTransformer(
    transformers=[
        ("num", "passthrough", numeric_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features)
    ]
)

model = Pipeline([
    ("preprocessor", preprocessor),
    ("regressor", LGBMRegressor(
        n_estimators=350,
        learning_rate=0.04,
        num_leaves=40,
        n_jobs=-1,
        random_state=42
    ))
])

# ============================================================
#           TRAINING
# ============================================================

print("[INFO] Training model...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model.fit(X_train, y_train)
y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
print(f"[RESULT] Training completed. MAE = {mae:.4f}")



joblib.dump(model, "ml_model.pkl")
print("[MODEL] Saved → ml_model.pkl")


try:
    feature_names = model.named_steps["preprocessor"].get_feature_names_out()
    importances = model.named_steps["regressor"].feature_importances_
    sorted_idx = importances.argsort()[::-1]

    print("\n[INFO] Top 15 most important features:")
    for i in sorted_idx[:15]:
        print(f" • {feature_names[i]} = {importances[i]:.4f}")

except Exception as e:
    print(f"[WARN] Could not compute feature importance: {e}")


