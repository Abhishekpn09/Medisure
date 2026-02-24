import pyodbc

cnx = pyodbc.connect(
   'DRIVER={ODBC Driver 17 for SQL Server};'
   'SERVER=LAPTOP-6MNJPHEQ;'
   'DATABASE=Medsurance;'
   'Trusted_Connection=yes;'
   'Encrypt=no;'
)

def get_all_locations():
   try:
       cursor = cnx.cursor()
       cursor.execute("SELECT DISTINCT county_name FROM Locations ORDER BY county_name")
       return [row[0].title() for row in cursor.fetchall()]
   except Exception as e:
       print("[ERROR] get_all_locations:", e)
       return []

def get_all_age_groups():
   try:
       cursor = cnx.cursor()
       cursor.execute("SELECT DISTINCT age_group FROM PlanPremiums ORDER BY age_group")
       return [int(row[0]) for row in cursor.fetchall()]
   except Exception as e:
       print("[ERROR] get_all_age_groups:", e)
       return []

def get_all_family_types():
   try:
       cursor = cnx.cursor()
       cursor.execute("SELECT DISTINCT family_type FROM PlanPremiums ORDER BY family_type")
       return [row[0].strip() for row in cursor.fetchall()]
   except Exception as e:
       print("[ERROR] get_all_family_types:", e)
       return []




def get_all_plan_types():
   try:
       cursor = cnx.cursor()
       cursor.execute("SELECT DISTINCT plan_type FROM Plans ORDER BY plan_type")
       return [row[0].strip().upper() for row in cursor.fetchall()]
   except Exception as e:
       print("[ERROR] get_all_plan_types:", e)
       return []




# -------------------------------------------------------
# PLAN QUERIES
# -------------------------------------------------------


def get_plan_by_id(plan_id):
   try:
       cursor = cnx.cursor()
       cursor.execute("SELECT * FROM Plans WHERE plan_id = ?", (plan_id,))
       row = cursor.fetchone()
       if row:
           cols = [col[0] for col in cursor.description]
           return dict(zip(cols, row))
       return None
   except Exception as e:
       print("[ERROR] get_plan_by_id:", e)
       return None




def get_csr_by_plan(plan_id, csr_variant):
   try:
       cursor = cnx.cursor()
       cursor.execute("""
           SELECT service_type, cost_type, value, unit, applies_after_deductible, unit_time
           FROM PlanCSR
           WHERE plan_id = ? AND csr_variant = ?
       """, (plan_id, csr_variant))


       rows = cursor.fetchall()
       if not rows:
           return []


       cols = [col[0] for col in cursor.description]
       return [dict(zip(cols, row)) for row in rows]
   except Exception as e:
       print("[ERROR] get_csr_by_plan:", e)
       return []




def get_premium_by_plan(plan_id, age_group, family_type):
   try:
       cursor = cnx.cursor()
       cursor.execute("""
           SELECT premium, ehb_percent
           FROM PlanPremiums
           WHERE plan_id = ? AND age_group = ? AND family_type = ?
       """, (plan_id, age_group, family_type))


       row = cursor.fetchone()
       if row:
           return {"premium": row[0], "ehb_percent": row[1]}
       return None


   except Exception as e:
       print("[ERROR] get_premium_by_plan:", e)
       return None




# -------------------------------------------------------
# MAIN PLAN SEARCH QUERY
# -------------------------------------------------------


def get_plans_for_criteria(plan_type, county_name, age_group, family_type):
   try:
       cursor = cnx.cursor()


       # get county code
       cursor.execute("SELECT county_code FROM Locations WHERE county_name = ?", (county_name,))
       row = cursor.fetchone()
       if not row:
           print("[INFO] No county code:", county_name)
           return []
       county_code = row[0]


       # join query
       query = """
           SELECT
               p.plan_id,
               p.plan_name,
               p.plan_type,
               p.meta_level,
               p.adult_dental,
               p.child_dental,
               p.benifits_summary_url,
               l.state_code,
               l.rating_area,
               pp.premium,
               pp.ehb_percent,
               ISNULL(csr.avg_copay, 0) AS avg_copay,
               ISNULL(csr.avg_coinsurance, 0) AS avg_coinsurance
           FROM Plans p
           JOIN PlanPremiums pp ON p.plan_id = pp.plan_id
           JOIN Locations l ON p.county_code = l.county_code
           LEFT JOIN (
               SELECT
                   plan_id,
                   AVG(CASE WHEN cost_type='Copay' THEN value END) AS avg_copay,
                   AVG(CASE WHEN cost_type='Coinsurance' THEN value END) AS avg_coinsurance
               FROM PlanCSR
               GROUP BY plan_id
           ) csr ON p.plan_id = csr.plan_id
           WHERE p.plan_type = ?
             AND p.county_code = ?
             AND pp.age_group = ?
             AND pp.family_type = ?
       """


       cursor.execute(query, (plan_type, county_code, age_group, family_type))
       rows = cursor.fetchall()


       if not rows:
           print(f"[INFO] No plans found for {plan_type}, {county_code}, {age_group}, {family_type}")
           return []


       cols = [col[0] for col in cursor.description]
       return [dict(zip(cols, row)) for row in rows]


   except Exception as e:
       print("[ERROR] get_plans_for_criteria:", e)
       return []
