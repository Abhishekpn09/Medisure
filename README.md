# Medisure Chatbot

## Project Overview

Medsurance is an AI-powered conversational assistant designed to simplify the often overwhelming process of exploring health insurance plans in the U.S.

Through natural language interaction, users can:

- Search for health insurance plans  
- Get premium estimates  
- View detailed plan information  
- Add or remove plans  
- Confirm selections  
- Track application status  

All interactions are handled through a conversational chatbot interface powered by Dialogflow and a FastAPI backend.

---

#  Project Structure

The project is modular and organized into clearly defined components:

### Folder Details

**backend/**  
Contains the FastAPI server that:
- Acts as the webhook for Dialogflow  
- Processes user intents  
- Queries the database  
- Formats structured responses  

**db/**  
Includes `DE.sql`, which:
- Defines the database schema  
- Contains sample health insurance plan data  
- Must be imported into SQL Server  

**dialogflow_assets/**  
Contains:
- Intents  
- Training phrases  
- Entity definitions  

These can be imported directly into Dialogflow.

**frontend/** *(optional)*  
Can be used to build a visual interface. The chatbot functions independently without it.

**notebooks/**  
Used during development for cleaning and transforming datasets downloaded from healthcare.gov.

---

# ⚙ Setting Up the Environment

##  Install Required Packages

Install dependencies using:

pip install -r backend/requirements.txt


---

# 🚀 Running the Backend (FastAPI)

1. Open terminal or command prompt  
2. Navigate to the backend directory:


The server will be available at:
http://127.0.0.1:8000/


---

# 🗃️ Setting Up the Database

The chatbot relies on SQL Server for storing and retrieving plan data.

## Steps:

1. Open SQL Server Management Studio or MySQL Workbench  
2. Load the SQL dump file:

db/DE.sql


This creates the following tables:

- Plans  
- PlanPremiums  
- PlanCSR  
- PlanLocations  
- Locations  

Ensure that database credentials inside:
<img width="940" height="411" alt="image" src="https://github.com/user-attachments/assets/8f4a11b8-39f8-413e-a8ab-d9836832a0d3" />


<img width="940" height="491" alt="image" src="https://github.com/user-attachments/assets/20f85215-919f-4a17-8066-a4dec200c1db" />
<img width="940" height="610" alt="image" src="https://github.com/user-attachments/assets/f41bdbab-d14b-4d73-a564-ae41d5afbe00" />
<img width="940" height="386" alt="image" src="https://github.com/user-attachments/assets/793e3ebd-ac4c-48b7-b06e-e9ead9d420ec" />
<img width="940" height="590" alt="image" src="https://github.com/user-attachments/assets/ea136dfe-4dbc-4046-8855-1fd0787664a8" />

backend/db_helper.py


match your local SQL configuration.

---

# 🌍 Connecting to Dialogflow

Dialogflow (ES or CX) is used to interpret user input and trigger backend logic.

Since Dialogflow requires a public webhook URL, expose your local FastAPI server using **ngrok**.

---

## 🔹 Running ngrok

1. Download from: https://ngrok.com/download  
2. Extract `ngrok.exe`  
3. Run:


4. Copy the generated HTTPS URL  
5. Set it as the webhook URL inside Dialogflow  

⚠️ Note: ngrok URLs expire. If expired, restart ngrok and update the webhook URL.

---

# 🤖 Dialogflow AI Setup

Dialogflow handles user interaction through **Intents** and **Entities**.

---

## Intents

| Intent Name | Description |
|-------------|------------|
| plan.search | Search plans by type and county |
| provide.agegroup | User specifies age group |
| provide.familytype | User specifies family type |
| plan.details | Retrieve metadata for a plan ID |
| plan.premium | Return premium and EHB % |
| plan.csr | Display cost-sharing reduction details |
| AddPlanToOrder | Add plan to user selection |
| RemovePlanFromOrder | Remove plan from selection |
| View-SelectedPlans | List selected plans |
| ConfirmPlanSelection | Confirm final submission |
| TrackPlanApplication | Track plan using application ID |

---

## Entities

| Entity | Example |
|--------|---------|
| plan-type | PPO, HMO |
| location | Autauga, Baldwin |
| age_group | 30-34 |
| family_type | Individual+2 children |
| plan-id | 14-character alphanumeric string |
| application_id | Tracking number |

Entities allow Dialogflow to extract structured parameters from user input.

---

# 🔄 System Flow

User Input  
→ Dialogflow Intent Detection  
→ Entity Extraction  
→ Webhook Call to FastAPI  
→ Backend Processing  
→ SQL Query Execution  
→ Response Formatting  
→ Returned to Dialogflow  
→ Displayed to User  

---

# ✅ Final Checklist

Before testing the chatbot:

- FastAPI server is running  
- SQL database is imported correctly  
- Database credentials are configured  
- ngrok is running  
- Webhook URL is set in Dialogflow  
- Intents and Entities are imported  

---

# 📌 Technologies Used

- Python  
- FastAPI  
- Uvicorn  
- SQL Server / MySQL  
- Dialogflow  
- ngrok  

---

## Author

Medsurance Chatbot Project  
Built using FastAPI, SQL, and Dialogflow




