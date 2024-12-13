### Development Setup Workflow for MVP

This workflow outlines the steps to set up the development environment and tools for building the MVP of the script breakdown SaaS platform.

---

#### **Technology Stack**
- **Programming Languages:** Python, JavaScript
- **Frameworks:** Flask (Python backend), React (JavaScript frontend)
- **Database:** MySQL
- **AI Model:** Google Gemini 2.0 (via API)
- **PDF Processing:** PyPDF2
- **API Integration:** Gemini 2.0 API keys

---

#### **Step 1: Development Environment Setup**
1. **Install Prerequisites:**
   - **Python (v3.9+):** [Download](https://www.python.org/downloads/) and install.
   - **Node.js:** [Download](https://nodejs.org/) and install (v16+ recommended).
   - **MySQL:** Install MySQL Server and set up a local or cloud instance.

2. **Set Up Virtual Environments:**
   - **Python:**
     ```bash
     python -m venv env
     source env/bin/activate  # For Linux/Mac
     env\Scripts\activate  # For Windows
     ```
   - **Node.js:** Use `nvm` for managing Node.js versions:
     ```bash
     nvm install 16
     nvm use 16
     ```

3. **Install Database Tools:**
   - Install MySQL Workbench for database management.

4. **Install Git:**
   - Set up Git for version control. [Download Git](https://git-scm.com/downloads).

---

#### **Step 2: Backend Setup (Flask)**
1. **Set Up Flask Project:**
   - Create a new Flask project directory:
     ```bash
     mkdir script_breakdown_backend
     cd script_breakdown_backend
     ```
   - Install Flask and dependencies:
     ```bash
     pip install flask flask-restful flask-cors PyPDF2 mysql-connector-python python-dotenv
     ```

2. **Environment Variables Configuration:**
   - Create a `.env` file:
     ```
     FLASK_APP=app.py
     FLASK_ENV=development
     MYSQL_HOST=localhost
     MYSQL_USER=root
     MYSQL_PASSWORD=Mostert51212!
     MYSQL_DB=script_breakdown
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

3. **Database Initialization:**
   - Create the database schema in MySQL:
     ```sql
     CREATE DATABASE script_breakdown;
     ```
   - Use a Python script or ORM (e.g., SQLAlchemy) to define and initialize tables.

4. **Flask API Endpoints:**
   - Implement endpoints for:
     - `/upload_script` (POST): Handles PDF uploads.
     - `/get_breakdown_data` (GET): Fetches breakdown data for specific roles.

---

#### **Step 3: Frontend Setup (React)**
1. **Set Up React Project:**
   - Create a new React app:
     ```bash
     npx create-react-app script-breakdown-frontend
     cd script-breakdown-frontend
     ```
   - Install dependencies:
     ```bash
     npm install axios react-router-dom dotenv
     ```

2. **Environment Variables:**
   - Create a `.env` file in the root directory:
     ```
     REACT_APP_API_BASE_URL=http://localhost:5000
     ```

3. **Component Structure:**
   - Set up folders for components, pages, and services:
     ```
     src/
     ├── components/
     ├── pages/
     ├── services/
     ├── App.js
     ├── index.js
     ```

4. **API Integration:**
   - Use `axios` for HTTP requests:
     ```javascript
     import axios from 'axios';

     const api = axios.create({
         baseURL: process.env.REACT_APP_API_BASE_URL,
     });

     export default api;
     ```

---

#### **Step 4: PDF Processing Integration**
1. **PDF Parsing with PyPDF2:**
   - Implement script parsing in Flask backend:
     ```python
     from PyPDF2 import PdfReader

     def parse_pdf(file_path):
         reader = PdfReader(file_path)
         text = ""
         for page in reader.pages:
             text += page.extract_text()
         return text
     ```

2. **Integration with Gemini API:**
   - Send parsed text to Gemini 2.0 for analysis:
     ```python
     import requests
     import os

     def analyze_script(parsed_text):
         api_key = os.getenv('GEMINI_API_KEY')
         response = requests.post(
             "https://api.gemini.com/analyze",
             headers={"Authorization": f"Bearer {api_key}"},
             json={"script_text": parsed_text}
         )
         return response.json()
     ```

---

#### **Step 5: Database Setup**
1. **Define Schema:**
   - Example schema for storing breakdown data:
     ```sql
     CREATE TABLE scripts (
         id INT AUTO_INCREMENT PRIMARY KEY,
         title VARCHAR(255) NOT NULL,
         upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     );

     CREATE TABLE breakdown_data (
         id INT AUTO_INCREMENT PRIMARY KEY,
         script_id INT,
         data JSON,
         FOREIGN KEY (script_id) REFERENCES scripts(id)
     );
     ```

2. **Connect Flask to MySQL:**
   - Use `mysql-connector-python`:
     ```python
     import mysql.connector
     from mysql.connector import Error

     def get_db_connection():
         return mysql.connector.connect(
             host=os.getenv('MYSQL_HOST'),
             user=os.getenv('MYSQL_USER'),
             password=os.getenv('MYSQL_PASSWORD'),
             database=os.getenv('MYSQL_DB')
         )
     ```

---

#### **Step 6: Running the Application**
1. **Start Backend:**
   ```bash
   flask run
   ```

2. **Start Frontend:**
   ```bash
   npm start
   ```

---

#### **Step 7: Testing the Setup**
1. **API Testing:**
   - Use Postman to test endpoints (`/upload_script`, `/get_breakdown_data`).

2. **Frontend Testing:**
   - Upload a PDF and verify the breakdown data is displayed correctly.

3. **Database Validation:**
   - Check MySQL tables for inserted records.

This setup ensures a smooth development environment for building the MVP while maintaining modularity and scalability.

