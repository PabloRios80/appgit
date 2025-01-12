import streamlit as st
import gspread
import json
import os
from google.oauth2.service_account import Credentials
import pandas as pd #Import para pandas
from datetime import datetime #Import para datetime

def connect_to_gsheet(spreadsheet_name, sheet_name):
    try:
        credentials_json = os.environ.get("GOOGLE_CREDENTIALS")

        if credentials_json:  # Streamlit Cloud (variables de entorno - JSON)
            try:
                credentials = Credentials.from_service_account_info(
                    json.loads(credentials_json),
                    scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                )
            except json.JSONDecodeError as e:
                st.error(f"Error al decodificar JSON de credenciales en Streamlit Cloud: {e}. Revisa el Secret GOOGLE_CREDENTIALS. Asegúrate de que no tenga comillas adicionales.")
                return None
        else:  # Local (secrets.toml - DICCIONARIO)
            try:
                from streamlit import secrets
                credentials = Credentials.from_service_account_info(
                    secrets["GOOGLE_CREDENTIALS"],
                    scopes=['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                )
            except FileNotFoundError:
                st.error("Error: Archivo secrets.toml no encontrado. Crea un archivo .streamlit/secrets.toml con tus credenciales (local).")
                return None
            except KeyError:
                st.error("Error: Credenciales no encontradas en secrets.toml. Verifica el formato y contenido (local).")
                return None
            except ModuleNotFoundError:
                st.error("Error: Streamlit no está instalado. Ejecuta 'pip install streamlit' (local).")
                return None

        gc = gspread.authorize(credentials)
        try:
          sh = gc.open(spreadsheet_name)
          worksheet = sh.sheet1 #Se selecciona la primera hoja
          return worksheet
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"Error: No se encontró la hoja de cálculo '{spreadsheet_name}'. Verifica el nombre.")
            return None

    except Exception as e:
        st.error(f"Error general al conectar con Google Sheets: {e}")
        return None
# Google Sheet credentials file
SPREADSHEET_NAME = 'miniforma'
SHEET_NAME = 'datos'

# Connect to the Google Sheet
sheet_by_name = connect_to_gsheet(SPREADSHEET_NAME,SHEET_NAME)

st.title("Beneficiarios")

# Form schema definition
form_schema = {
   "task_name": {
       "type": "text",
       "label": "Task Name",
       "required": True,
       "validation": {
           "min_length": 3,
           "max_length": 50,
           "message": "Task name must be between 3 and 50 characters."
       } 
   },
   "project": {
       "type": "select",
       "label": "Project",
       "required": True,
       "options": ["Project A", "Project B", "Project C"],
       "validation": {
           "message": "Please select a project."
       }
   },
   "due_date": {
       "type": "date",
       "label": "Due Date",
       "required": True,
       "validation": {
           "message": "Due date must be a valid date in the future."
       }
   },
   "description": {
       "type": "textarea",
       "label": "Description",
       "required": False,
       "validation": {
           "max_length": 200,
           "message": "Description cannot exceed 200 characters."
       }
   }
}


# Read Data from Google Sheets
def read_data():
    data = sheet_by_name.get_all_records()  
    return pd.DataFrame(data)

# Add Data to Google Sheets
def add_data(row):
    sheet_by_name.append_row(row)

# Render the form using the schema inside a form container
def render_form(schema):
    form_data = {}
    st.sidebar.header("Task  Form")
    with st.sidebar.form(key="task_form"):

        
        for field, properties in schema.items():
            field_type = properties["type"]
            label = properties["label"]
            
            if field_type == "text":
                form_data[field] = st.text_input(label)
            elif field_type == "select":
                options = properties["options"]
                form_data[field] = st.selectbox(label, options)
            elif field_type == "date":
                form_data[field] = st.date_input(label, datetime.today())
            elif field_type == "textarea":
                form_data[field] = st.text_area(label)
        
        submitted = st.form_submit_button("Submit")
    
    return form_data, submitted

# Validate the form based on the schema
def validate_form(form_data, schema):
    errors = []
    for field, value in form_data.items():
        properties = schema[field]
        if properties.get("required") and not value:
            errors.append(f"{properties['label']} is required.")
        
        # Custom validation for each field type
        if properties["type"] == "text":
            min_len = properties["validation"].get("min_length", 0)
            max_len = properties["validation"].get("max_length", float('inf'))
            if not (min_len <= len(value) <= max_len):
                errors.append(properties["validation"]["message"])
        elif properties["type"] == "date":
            if value < datetime.today().date():
                errors.append(properties["validation"]["message"])
    
    return errors

# Render the form
form_data, submitted = render_form(form_schema)

# Handle form submission
if submitted:
    errors = validate_form(form_data, form_schema)
    if errors:
        for error in errors:
            st.sidebar.error(error)
    else:
        st.success("Form submitted successfully!")
        # st.write("Form Data:", form_data)
        
        # Add the form data to Google Sheets
        row = [
            form_data['task_name'],  # Task Name
            form_data['project'],    # Project
            form_data['due_date'].strftime('%Y-%m-%d'),  # Due Date
            form_data.get('description', "")  # Description (optional)
        ]
        
        add_data(row)  # Add data to Google Sheets
        st.write("Data successfully added to Google Sheets!")
        df = read_data()  # Re-read the data after submission

# Display data in the main view
st.header("Data Table")
df = read_data()

st.dataframe(df, width=900, height=600)  # Display the data in a table