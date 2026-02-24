from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime
import db_helper
import ml_model
import time
import re

app = FastAPI()

# -------------------------------------------------
# In-memory user sessions
# -------------------------------------------------
user_sessions = {}

# -------------------------------------------------
# BASIC ROUTES
# -------------------------------------------------
@app.get("/")
async def root():
    return {"message": "API is running."}

@app.get("/ping")
async def ping():
    return {"status": "ok"}

# -------------------------------------------------
# MAIN WEBHOOK
# -------------------------------------------------
@app.post("/")
async def handle_request(request: Request):
    try:
        payload = await request.json()

        # Print full payload for debugging
        print("\n================ RAW WEBHOOK PAYLOAD ================\n")
        print(payload)
        print("\n=====================================================\n")

        query_result = payload.get("queryResult", {})
        intent = query_result.get("intent", {}).get("displayName")
        parameters = query_result.get("parameters", {}) or {}
        session_id = payload.get("session", "default_session")
        raw_text = query_result.get("queryText", "") or ""
        parameters["_raw_text"] = raw_text
        print("➡ Intent:", intent)
        print("➡ Parameters:", parameters)
        print("➡ Session ID:", session_id)

        get_session(session_id)

        intent_handler_dict = {
            "plan.search": lambda p: search_plan(p, session_id),
            "provide.agegroup": lambda p: provide_agegroup(p, session_id),
            "provide.familytype": lambda p: provide_familytype(p, session_id),
            "AddPlanToOrder": lambda p: add_plan_to_order(p, session_id),
            "RemovePlanFromOrder": lambda p: remove_plan_from_order(p, session_id),
            "View-SelectedPlans": lambda p: view_selected_plans(p, session_id),
            "ConfirmPlanSelection": lambda p: confirm_plan_selection(p, session_id),
        }

        if intent in intent_handler_dict:
            return intent_handler_dict[intent](parameters)

        return JSONResponse({"fulfillmentText": "Sorry, I didn’t understand your request."})

    except Exception as e:
        print("ERROR in handle_request:", e)
        return JSONResponse({"fulfillmentText": f"An internal error occurred: {str(e)}"})


# -------------------------------------------------
# INTENT HANDLERS
# -------------------------------------------------
def search_plan(parameters, session_id):
    plan_type_raw = parameters.get("plan-type", "")
    location_raw = parameters.get("location", "")

    plan_type = plan_type_raw.split(":")[0].strip().lower()
    location = (location_raw or "").strip().title()

    valid_plan_types = [p.lower() for p in db_helper.get_all_plan_types()]
    valid_locations = db_helper.get_all_locations()

    if plan_type not in valid_plan_types:
        return JSONResponse({"fulfillmentText": "That plan type is not available."})

    if location not in valid_locations:
        return JSONResponse({"fulfillmentText": "That location is not available."})

    session = user_sessions[session_id]
    session["plan_type"] = plan_type
    session["location"] = location

    return JSONResponse({"fulfillmentText": "Got it! Please provide your age group."})


def provide_agegroup(parameters, session_id):
    user_sessions[session_id]["age_group"] = parameters.get("age_group")
    return JSONResponse({"fulfillmentText": "Thank you! Now provide your family type."})


def provide_familytype(parameters, session_id):
    try:
        family_type = parameters.get("family_type")
        session = user_sessions[session_id]
        session["family_type"] = family_type

        plan_type = session.get("plan_type")
        location = session.get("location")
        age_group = session.get("age_group")

        if not all([plan_type, location, age_group, family_type]):
            return JSONResponse({"fulfillmentText": "Missing required information."})

        age_value = normalize_age_group(age_group)

        # SQL
        plans = db_helper.get_plans_for_criteria(
            plan_type.upper(),          # DB has PPO uppercase usually
            location,
            age_value,
            family_type.strip()
        )

        if not plans:
            return JSONResponse({"fulfillmentText": "No plans found matching your criteria."})

        # ML ranking
        ranked_plans = recommend_best_plans(session_id, plans)

        # IMPORTANT: store last recommendations so AddPlanToOrder works reliably
        session["last_recommended"] = ranked_plans

        plan_text_lines = []
        for i, p in enumerate(ranked_plans, start=1):
            plan_text_lines.append(
                f"{i}) {p.get('plan_name','N/A')}. "
                f"Level: {p.get('meta_level','N/A')}. "
                f"Premium: ${p.get('premium','N/A')}. "
                f"Summary: {p.get('benifits_summary_url','N/A')}"
            )

        plan_text = "\n".join(plan_text_lines)

        return JSONResponse({
            "fulfillmentText": (
                "Here are your top recommended plans:\n"
                f"{plan_text}\n\n"
                #"You can say: Add plan 1 (or 2/3) OR Add <plan name>."
            )
        })

    except Exception as e:
        print("[ERROR] provide_familytype failed:", e)
        return JSONResponse({"fulfillmentText": f"Error while finding plans: {str(e)}"})


# -------------------------------------------------
# ML RECOMMENDATION
# -------------------------------------------------
def recommend_best_plans(session_id, plans):
    session = user_sessions[session_id]
    age = normalize_age_group(session.get("age_group"))
    family_type = session.get("family_type")

    user_profile = {"age": age, "family_type": family_type}

    for plan in plans:
        plan["ml_score"] = ml_model.predict_plan_score(plan, user_profile)

    return sorted(plans, key=lambda x: x.get("ml_score", 0), reverse=True)[:3]


# -------------------------------------------------
# CART HANDLERS
# -------------------------------------------------
def add_plan_to_order(parameters, session_id):
    session = user_sessions[session_id]
    last_recommended = session.get("last_recommended") or []

    raw_text = (parameters.get("_raw_text") or "").strip()

    # Dialogflow parameters (can be missing / inconsistent)
    plan_name = parameters.get("plan_name") or parameters.get("plan-name")
    plan_index = parameters.get("plan-index") or parameters.get("plan_index")
    plan_id = parameters.get("plan-id") or parameters.get("plan_id")

    # If Dialogflow didn't capture, parse from raw text
    if not plan_index:
        m = re.search(r"\bplan\s*(\d+)\b", raw_text.lower())
        if m:
            plan_index = m.group(1)

    if not plan_name:
        # handle: "Add Blue HSA Bronze" / "Add Blue HSA Bronze plan"
        m = re.search(r"^\s*add\s+(.+?)\s*(?:plan)?\s*$", raw_text, flags=re.I)
        if m:
            plan_name = m.group(1).strip()

    chosen_plan = None

    # 1) choose by index (from recommendations)
    if plan_index and last_recommended:
        try:
            idx = int(float(str(plan_index).strip())) - 1  # handles "2.0"
            if 0 <= idx < len(last_recommended):
                chosen_plan = last_recommended[idx]
        except Exception:
            pass

    # 2) choose by plan name (from recommendations) - fuzzy contains
    if chosen_plan is None and plan_name and last_recommended:
        target = str(plan_name).strip().lower()
        for p in last_recommended:
            cand = str(p.get("plan_name", "")).strip().lower()
            if target == cand or target in cand or cand in target:
                chosen_plan = p
                break

    # 3) choose by plan_id from DB
    if chosen_plan is None and plan_id:
        chosen_plan = db_helper.get_plan_by_id(str(plan_id).strip())

    if chosen_plan is None:
        return JSONResponse(content={
            "fulfillmentText": (
                "Please add a plan by number (e.g., Add plan 1) or by name (e.g., Add Blue HSA Bronze). "
                "If you haven’t requested recommendations yet, ask for plans first."
            )
        })

    # Store selection (single-plan cart)
    selected_obj = {
        "plan_id": chosen_plan.get("plan_id"),
        "plan_name": chosen_plan.get("plan_name"),
        "meta_level": chosen_plan.get("meta_level"),
        "premium": chosen_plan.get("premium"),
        "benifits_summary_url": chosen_plan.get("benifits_summary_url"),
    }
    session["selected_plans"] = [selected_obj]

    return JSONResponse(content={
        "fulfillmentText": (
            f" {selected_obj['plan_name']} added. "
            f"Level: {selected_obj.get('meta_level','N/A')} "
            f"Premium: ${selected_obj.get('premium','N/A')}\n"
            f"Summary: {selected_obj.get('benifits_summary_url','N/A')}\n\n"
            "You can say: View selected plans, Remove plan, or Confirm."
        )
    })


def remove_plan_from_order(parameters, session_id):
    session = user_sessions[session_id]
    plans = session.get("selected_plans", [])

    if not plans:
        return JSONResponse(content={"fulfillmentText": "Your cart is already empty."})

    session["selected_plans"] = []

    # IMPORTANT: keep last_recommended so user can add another plan without re-searching
    return JSONResponse(content={
        "fulfillmentText": (
            "The selected plan has been successfully removed.\n"
            "You can now say: Add plan 1/2/3 or Add <plan name>, or ask for recommendations again."
        )
    })


def view_selected_plans(parameters, session_id):
    session = user_sessions[session_id]
    plans = session.get("selected_plans", [])

    if not plans:
        return JSONResponse(content={"fulfillmentText": "Your cart is empty. Add a plan first."})

    lines = []
    for idx, p in enumerate(plans, start=1):
        lines.append(
            f"{idx}) {p.get('plan_name','N/A')} "
            f"Level: {p.get('meta_level','N/A')} "
            f"Premium: ${p.get('premium','N/A')} "
            f"Summary: {p.get('benifits_summary_url','N/A')}"
        )

    return JSONResponse(content={
        "fulfillmentText": (
            "Your selected plan:\n" + "\n".join(lines) +
            "\n\nYou can say: Remove plan or Confirm."
        )
    })


def confirm_plan_selection(parameters, session_id):
    session = user_sessions[session_id]
    plans = session.get("selected_plans", [])

    if not plans:
        return JSONResponse(content={"fulfillmentText": "No plan selected to confirm."})

    p = plans[0]
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    msg = (
        "Your plan has been confirmed!\n"
        f"Plan: {p.get('plan_name','N/A')}\n"
        f"Level: {p.get('meta_level','N/A')}\n"
        f"Premium: ${p.get('premium','N/A')}\n"
        f"Summary: {p.get('benifits_summary_url','N/A')}\n"
        f"Confirmed on: {timestamp}\n"
        "Thank you for using Medisure."
    )

    # reset session
    del user_sessions[session_id]
    return JSONResponse(content={"fulfillmentText": msg})


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def get_session(session_id):
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            "plan_type": None,
            "location": None,
            "age_group": None,
            "family_type": None,
            "selected_plans": [],
            "last_recommended": []
        }
    return user_sessions[session_id]


def normalize_age_group(age_group):
    if not age_group:
        return None

    s = str(age_group).replace("–", "-").strip()

    if s.isdigit():
        return int(s)

    if "-" in s:
        try:
            a, b = s.split("-")
            return (int(a) + int(b)) // 2
        except Exception:
            pass

    nums = re.findall(r"\d+", s)
    return int(nums[0]) if nums else None
