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
