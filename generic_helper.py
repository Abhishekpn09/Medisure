# generic_helper.py

def format_plan_list(plans):
    try:
        plan_lines = [f"- {plan['plan_name']} (ID: {plan['plan_id']})" for plan in plans]
        return "\n".join(plan_lines)
    except Exception as e:
        return "Error formatting plans."

def format_currency(value):
    try:
        return "${:,.2f}".format(value)
    except Exception as e:
        return f"{value}"






