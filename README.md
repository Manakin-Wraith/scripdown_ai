# ScriptDown AI

ScriptDown AI is a SaaS platform designed to automate the script breakdown process for independent filmmakers. The platform utilizes AI, specifically Google Gemini 2.0, to analyze uploaded PDF scripts and extract key production data. This tool aims to enhance pre-production efficiency by providing detailed breakdowns tailored to various Head of Department (HOD) roles.

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [API Endpoints](#api-endpoints)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Script Upload and Parsing:** Upload scripts in PDF format and extract text content.
- **AI-Based Script Breakdown:** Automatically tag and identify script elements using Google Gemini 2.0.
- **Role-Specific Dashboards:** Display extracted breakdown data relevant to key HOD roles.
- **Collaboration Tools:** Enable team members to comment and annotate on breakdown elements.
- **Breakdown Sheets Generation:** Automatically generate breakdown sheets summarizing extracted elements.
- **Export Functionality:** Export breakdown data into PDF and Excel/CSV files.
- **User Authentication:** Basic user authentication (sign-up, login) to secure access to the platform.
- **Simple UI/UX:** User-friendly interface for uploading scripts, viewing breakdowns, and accessing dashboards.

## Technology Stack

- **Programming Languages:** Python, JavaScript
- **Frameworks:** Flask (Python backend), React (JavaScript frontend)
- **Database:** MySQL
- **AI Model:** Google Gemini 2.0 (via API)
- **PDF Processing:** PyPDF2
- **API Integration:** Gemini 2.0 API keys

## Project Structure

```
script_breakdown/
├── backend/                      # Backend application (Flask)
│   ├── app.py                    # Main Flask application file
│   ├── __init__.py
│   ├── config.py                 # Configuration settings
│   ├── routes/                   # API endpoint definitions
│   │   ├── script_routes.py      # Routes for script upload and breakdown
│   │   └── auth_routes.py        # Routes for authentication
│   ├── models/                   # Database model definitions
│   │   ├── script.py             # Script model
│   │   ├── scene.py              # Scene model
│   │   ├── hod_notes.py          # HOD notes models (director, producer, etc.)
│   │   ├── user.py
│   │   └── user_roles.py
│   ├── services/                 # Business logic modules
│   │   ├── script_service.py     # Script processing logic
│   │   ├── gemini_service.py     # Gemini API integration
│   │   └── auth_service.py       # Authentication related service calls
│   ├── utils/                    # Utility functions for the backend
│   │   ├── pdf_parser.py         # PDF parsing functionality
│   │   ├── auth_helper.py        # Auth Helper functions
│   │   └── error_handler.py      # Error handling
│   ├── db/                       # Database related files
│   │   ├── __init__.py
│   │   └── db_connection.py      # Database connection and configuration
│   ├── tests/                    # Backend unit tests
│   │   └── ...                   # tests here
│   ├── .env                      # Environment variables
│   └── requirements.txt          # Python dependencies

├── frontend/                     # Frontend application (React)
│   ├── src/
│   │   ├── components/           # Reusable UI components
│   │   │   ├── common/           # Common UI elements
│   │   │   │   ├── Button.js
│   │   │   │   ├── Input.js
│   │   │   │   ├── Modal.js
│   │   │   │   └── LoadingSpinner.js
│   │   │   ├── layout/           # Components to manage overall layout
│   │   │   │   ├── Header.js
│   │   │   │   ├── Sidebar.js
│   │   │   │   └── Footer.js
│   │   │   ├── script_breakdown/ # Script breakdown process components
│   │   │   │   ├── ScriptUpload.js
│   │   │   │   ├── SceneSummary.js
│   │   │   │   ├── BreakdownTable.js
│   │   │   │   ├── RoleDashboard.js
│   │   │   │   ├── BreakdownComment.js
│   │   │   │   └── HOD_components/ # Specific hod components
│   │   │   │       ├── DirectorDashboard.js
│   │   │   │       ├── ProducerDashboard.js
│   │   │   │       ├── ProductionDesignerDashboard.js
│   │   │   │       └── ...other HOD dashboard components
│   │   │   └── auth/             # Authentication components
│   │   │       ├── LoginForm.js
│   │   │       └── SignUpForm.js
│   │   ├── containers/           # Components that manage state/logic and compose other components
│   │   │   ├── ScriptContainer.js
│   │   │   ├── DashboardContainer.js
│   │   │   └── AuthContainer.js
│   │   ├── pages/                # Top-level components for different routes
│   │   │   ├── HomePage.js
│   │   │   ├── ScriptPage.js
│   │   │   ├── AuthPage.js
│   │   │   └── NotFoundPage.js
│   │   ├── context/              # Context API components for global state
│   │   │   └── AuthContext.js
│   │   ├── services/             # Modules to handle API calls and business logic
│   │   │   ├── apiService.js
│   │   │   └── authService.js
│   │   ├── utils/                # Utility functions
│   │   │   └── helpers.js
│   │   ├── App.js
│   │   └── index.js
│   │   └── index.css
│   ├── public/                   # Static assets
│   │   └── ...
│   ├── tests/                    # Frontend unit tests
│   │   └── ...                   # tests here
│   ├── .env                      # Environment variables
│   └── package.json              # Node.js dependencies

├── documentation/                # Project documentation
│   ├── api_docs.md               # API documentation
│   ├── database_schema.md        # Database schema details
│   └── ...

├── .gitignore                    # Git ignore file
└── 

README.md

                     # Project README
```

## Setup Instructions

### Development Environment Setup

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

### Backend Setup (Flask)

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

### Frontend Setup (React)

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

### Running the Application

1. **Start Backend:**
   ```bash
   flask run
   ```

2. **Start Frontend:**
   ```bash
   npm start
   ```

## API Endpoints

For detailed API endpoint information, refer to the 

API_endpoints.md

 file.

## Usage

1. **Upload a Script:**
   - Navigate to the script upload page and upload a PDF script.
   - The script will be parsed and processed by the backend.

2. **View Breakdown Data:**
   - Access role-specific dashboards to view the extracted breakdown data.

3. **Collaborate:**
   - Add comments and annotations to specific scenes and breakdown elements.

4. **Export Data:**
   - Export breakdown data into PDF or Excel/CSV files for offline use.

## Contributing

Contributions are welcome! Please read the `CONTRIBUTING.md` file for guidelines on how to contribute to this project.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
```

This `README.md` file provides a comprehensive overview of the project, including its features, technology stack, setup instructions, and usage guidelines.
