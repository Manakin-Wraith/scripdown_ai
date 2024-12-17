**Phase 1: Environment Setup & Core Backend (1-2 Weeks)**

**1. Project Initialization (1 Day)**

*   **Task 1.1:** Install Python (v3.9+)
    *   **Details:** Download and install Python from the official website, verify installation.
    *   **Owner:** (Assign to specific team member)
*   **Task 1.2:** Install Node.js (v16+)
    *   **Details:** Download and install Node.js (with `npm`), verify installation.
    *   **Owner:**
*   **Task 1.3:** Install MySQL
    *   **Details:** Download and install MySQL server, set up a local instance.
    *   **Owner:**
*   **Task 1.4:** Install Git
    *   **Details:** Download and install Git, set up basic Git configuration
    *    **Owner:**
*   **Task 1.5:** Create Project Directories
    *   **Details:** Create `script_breakdown_backend` and `script_breakdown_frontend` directories.
    *   **Owner:**
*   **Task 1.6:** Create Virtual Environments
    *   **Details:** Set up isolated Python and Node.js virtual environments.
    *   **Owner:**

**2. Database Setup (1-2 Days)**

*   **Task 2.1:** Create Database
    *   **Details:** Create the `script_breakdown` database in MySQL.
    *   **Owner:**
*   **Task 2.2:** Define Schema
    *   **Details:** Create the SQL scripts for all tables (`scripts`, `scenes`, `director_notes`, etc) as per the database schema provided.
    *   **Owner:**
*   **Task 2.3:** Run SQL Scripts
    *   **Details:** Execute the SQL scripts to create tables and relationships in MySQL.
    *   **Owner:**

**3. Backend - Flask Project Setup (1 Day)**

*   **Task 3.1:** Create Flask Project
    *   **Details:** Initialize a Flask project in `script_breakdown_backend`.
    *   **Owner:**
*   **Task 3.2:** Install Flask Dependencies
    *   **Details:** Install `flask`, `flask-restful`, `flask-cors`, `PyPDF2`, `mysql-connector-python`, `python-dotenv`.
    *   **Owner:**
*   **Task 3.3:** Create .env File
    *   **Details:** Create a `.env` file and add environment variables (MySQL, API key).
    *   **Owner:**

**4. Backend - Core API Endpoints (2-3 Days)**

*   **Task 4.1:** Implement `/upload_script` Endpoint (Structure Only)
    *   **Details:** Set up basic POST route to accept PDF files.
    *   **Owner:**
*   **Task 4.2:** Implement `/get_breakdown_data` Endpoint (Structure Only)
    *   **Details:** Set up basic GET route with script ID and role as parameters.
    *   **Owner:**
*  **Task 4.3:** Implement Database Connection
    * **Details:** Use the `mysql-connector-python` to set up a database connection.
    *   **Owner:**

**5. API Key Integration (1 Day)**

*   **Task 5.1:** Configure API Keys
    *   **Details:** Load API keys from the `.env` file, create utility function for Gemini API calls.
    *   **Owner:**
*  **Task 5.2:** Verify Gemini API Key
   *   **Details:** Test that the Gemini API Key works by making a sample API call
   *   **Owner:**

**6. Backend - Script Parsing and Data Extraction (2-3 Days)**

*   **Task 6.1:** PDF Parsing with PyPDF2
    *   **Details:** Implement the `parse_pdf` function to extract text from PDF.
    *   **Owner:**
*   **Task 6.2:** Gemini API Integration
    *   **Details:**
        *   Modify `/upload_script` to send parsed text to the Gemini API.
        *   Structure and store the data in the database.
    *   **Owner:**
*   **Task 6.3:** Error Handling
    *   **Details:** Implement error handling in API calls and database operations.
    *   **Owner:**

**7. Testing (1 Day)**

*   **Task 7.1:** API Testing with Postman
    *   **Details:** Test `/upload_script` and `/get_breakdown_data` endpoints to ensure correct functionality.
    *   **Owner:**

**Phase 2: Frontend Development (2-3 Weeks)**

**1. React Project Setup (1 Day)**

*   **Task 1.1:** Create React Application
    *   **Details:** Initialize a React application using `create-react-app` in the `script_breakdown_frontend` directory.
    *   **Owner:**
*   **Task 1.2:** Install Dependencies
    *   **Details:** Install `axios`, `react-router-dom`, `dotenv`.
    *   **Owner:**
*   **Task 1.3:** Set Environment Variables
    *   **Details:** Set up a `.env` file with the API base URL.
    *   **Owner:**

**2. Component Structure (2-3 Days)**

*   **Task 2.1:** Create `common` Components
    *   **Details:** Build `Button.js`, `Input.js`, `Modal.js`, `LoadingSpinner.js`.
    *   **Owner:**
*  **Task 2.2:** Create `layout` Components
    *   **Details:** Build `Header.js`, `Sidebar.js`, `Footer.js`.
    *   **Owner:**
*   **Task 2.3:** Create Script Breakdown Components
    *   **Details:** Build `ScriptUpload.js`, `SceneSummary.js`, `BreakdownTable.js`, `RoleDashboard.js`, `BreakdownComment.js`, and all the HOD dashboard components
    *   **Owner:**
*   **Task 2.4:** Create Auth Components
    *   **Details:** Build `LoginForm.js` and `SignupForm.js`.
    *   **Owner:**
*   **Task 2.5:** Create Container Components
    *   **Details:** Build `ScriptContainer.js`, `DashboardContainer.js`, `AuthContainer.js`.
    *   **Owner:**
*   **Task 2.6:** Create Page Components
    *   **Details:** Build `HomePage.js`, `ScriptPage.js`, `AuthPage.js`, and `NotFoundPage.js`.
    *   **Owner:**
*   **Task 2.7:** Create Context Components
    *   **Details:** Build `AuthContext.js`.
    *  **Owner:**
*   **Task 2.8:** Create Services and Utils
   * **Details:** Build `apiService.js`, `authService.js` and `helpers.js`.
   * **Owner:**

**3. API Integration (3-4 Days)**

*   **Task 3.1:** Implement `apiService`
    *   **Details:** Create functions for making API calls with `axios`.
    *   **Owner:**
*   **Task 3.2:** Implement `authService`
   *  **Details:** Create functions for making authentication related calls
   * **Owner:**
*   **Task 3.3:** Integrate Script Upload
    *   **Details:** Connect the `ScriptUpload` component to the `/upload_script` endpoint.
    *   **Owner:**
*   **Task 3.4:** Integrate Dashboard Data Fetching
    *   **Details:** Use the `apiService` to connect `RoleDashboard` with `/get_breakdown_data` endpoint.
    *   **Owner:**

**4. User Authentication (2 Days)**

*   **Task 4.1:** Implement Login Form
    *   **Details:** Create the `LoginForm` using `AuthContainer`.
    *   **Owner:**
*   **Task 4.2:** Implement Signup Form
    *   **Details:** Create the `SignupForm` using `AuthContainer`.
    *   **Owner:**
*   **Task 4.3:** Implement Auth Context
    *   **Details:** Setup a context to handle the auth state
    *    **Owner:**
*   **Task 4.4:** Implement Authentication Flow
    *   **Details:** Make use of `authService` to implement the required auth flow.
    *   **Owner:**

**5. Script Upload & Display (2-3 Days)**

*   **Task 5.1:** Implement Script Upload Functionality
    *   **Details:** Make the `ScriptUpload` component working to upload a script.
    *   **Owner:**
*   **Task 5.2:** Implement Dashboard Navigation
    *   **Details:** Implement `DashboardContainer` component to navigate to different HOD dashboards.
    *   **Owner:**
*   **Task 5.3:** Display Breakdown Data
    *   **Details:** Use `RoleDashboard` component to fetch data and `BreakdownTable` component to display data.
    *   **Owner:**

**6. Collaboration Features (Basic) (1-2 Days)**

*   **Task 6.1:** Implement `BreakdownComment` Component
    *   **Details:** Allow users to add comments for scenes using `BreakdownComment`.
    *   **Owner:**
*   **Task 6.2:** Display Comments
    *   **Details:** Display the comments relevant to a scene.
    *   **Owner:**

**7. Frontend Testing (1 Day)**

*   **Task 7.1:** Component Testing
    *   **Details:** Ensure all components function as intended.
    *   **Owner:**
*   **Task 7.2:** UI Responsiveness Testing
    *   **Details:** Check the responsiveness on different screen sizes.
    *   **Owner:**
*  **Task 7.3:** API Integration Testing
   * **Details:** Ensure that the API calls work and data is displayed correctly
   * **Owner:**

**Phase 3: Export & Deployment (1-2 Weeks)**

**1. Export Functionality (2-3 Days)**

*   **Task 1.1:** Implement PDF Export
    *   **Details:** Add export buttons and create a backend API to create PDF.
    *   **Owner:**
*   **Task 1.2:** Implement Excel Export
    *   **Details:** Add export buttons and create a backend API to create Excel file.
    *   **Owner:**
*   **Task 1.3:** Customize Data for Export
    *   **Details:** Allow users to select data for export based on their role.
    *   **Owner:**

**2. Deployment Setup (2-3 Days)**

*   **Task 2.1:** Choose Deployment Platform
    *   **Details:** Select a suitable deployment platform.
    *   **Owner:**
*   **Task 2.2:** Configure Backend for Deployment
    *   **Details:** Set up backend environment variables for production.
    *   **Owner:**
*   **Task 2.3:** Configure Frontend for Deployment
    *   **Details:** Set up frontend build process for deployment.
    *   **Owner:**
*   **Task 2.4:** Deploy the Application
    *   **Details:** Deploy the application to the selected platform.
    *   **Owner:**

**3. Deployment Testing (1-2 Days)**

*   **Task 3.1:** End-to-End Testing
    *   **Details:** Test all functionalities from the live environment.
    *   **Owner:**
*   **Task 3.2:** User Testing
   *   **Details:** Have a user test all functionalities in the live environment
   *    **Owner:**

**4. Documentation (1 Day)**

*   **Task 4.1:** Create Developer README
    *   **Details:** Create "How to set up local dev environment" and "How to deploy." documentation
    *   **Owner:**

**Tracking and Management:**

*   **Project Management Tool:** Use a project management tool (e.g., Jira, Trello, Asana) to assign owners, set due dates, and track progress.
*   **Daily Standups:** Hold daily standups to discuss progress and blockers.
*   **Code Reviews:** Implement code reviews before merging changes to the main branch.

This detailed breakdown should provide a clearer path to building the ScriptDown MVP. Remember to adapt it to your team's specific needs and working style.
