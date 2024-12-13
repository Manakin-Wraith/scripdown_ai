MVP Instructions

Overview

This document outlines the steps for building the MVP of a SaaS platform designed to automate the script breakdown process for independent filmmakers. The platform will utilize AI, specifically Google Gemini 2.0, to analyze uploaded PDF scripts and extract key production data. The goal is to create a functional tool that demonstrates the core capabilities of automated script breakdown, pre-production efficiency, and detail capture.

Technology Stack
	•	Programming Languages: Python, JavaScript
	•	Frameworks: Flask or Django (Python backend), React or Vue.js (JavaScript frontend)
	•	Database: PostgreSQL or MySQL
	•	AI Model: Google Gemini 2.0 (via API)
	•	PDF Processing: PyPDF2 or similar library
	•	API Integration: Use your provided Gemini 2.0 API keys for integration

Setup
	1.	Development Environment:
Set up a local development environment with Python, Node.js (or equivalent for chosen JS framework), and a database server.
	2.	Database Setup:
Create a database schema as per the schema provided separately. Ensure the database is properly connected to your backend application.
	3.	API Keys Configuration:
Securely configure the Gemini 2.0 API keys within your backend environment. Do not expose them directly in the frontend code or commit them to your repository. Use environment variables for secure handling.
	4.	Package Installation:
Install all necessary libraries and packages for your chosen frameworks and dependencies (e.g., Flask, React, psycopg2, PyPDF2).

Backend Development
	•	Script Upload Parsing:
Implement functionality to handle PDF uploads. Use the PyPDF2 (or similar) library to extract the text content of the script. The parsed script should be stored as a string for processing.
	•	API Integration (Gemini 2.0):
Integrate the Gemini 2.0 API using your provided API keys to send the parsed text. Structure the API call to receive the extracted data from Gemini in a structured format (JSON).
	•	Data Extraction and Processing:
Use the Gemini 2.0 API to analyze the script text and extract key information:
	•	Scene settings (interior/exterior, location descriptions)
	•	Characters (speaking and non-speaking)
	•	Props
	•	Dialogue
	•	Action lines that may suggest visual or audio elements
Structure and store the extracted data in your database.
	•	Role-Specific Data Structure:
Create functions or data structures that organize extracted data according to HOD roles (Director, Producer, Production Designer, etc.).
	•	API Endpoints:
	•	/upload_script: Handles the script upload and processing.
	•	/get_breakdown_data: Retrieves breakdown data for a specific HOD.
	•	Data Handling:
Ensure proper error handling for PDF parsing, API calls, and data storage. Use try-except blocks for exceptions and return helpful error responses to the front end.
	•	Authentication:
Implement basic user authentication and authorization to ensure only valid users access the platform.

Frontend Development
	•	User Interface:
Develop a user-friendly interface for script upload, data review, and team collaboration tools.
	•	Role-Based Dashboards:
Create dashboards that display relevant breakdown information tailored to specific roles (e.g., Director, Producer, Production Designer).
	•	Script Upload:
Implement file upload functionality to send the PDF script to the backend API for processing.
	•	Data Display:
Create components to display extracted data in a structured and role-specific manner using tables, lists, or other suitable UI elements.
	•	Collaboration Features:
Provide tools for team members to add comments and annotations for specific scenes, with visibility across relevant dashboards.
	•	Dashboard Implementation:
Develop a main dashboard for accessing all role-based dashboards.
	•	API Integration (Frontend):
Connect the frontend to backend API endpoints and handle error checking.
	•	Responsive Design:
Ensure the application works well on different screen sizes.
	•	State Management:
Use a state management solution (e.g., React Context API, Vuex) for storing, accessing, and updating data.

Collaboration
	•	Commenting and Annotations:
Enable users to add comments and annotations to scenes and breakdown elements.
	•	Task Assignment:
Allow users to assign tasks to team members.

Export Functionality
	•	PDF and Excel Export:
Provide export options for reports, customized for specific roles. For example:
	•	Director: Scene summaries, emotional beats, shot suggestions (PDF).
	•	Production Designer: Props, set dressing, and locations (CSV).
	•	Report Customization:
Allow users to select data for inclusion in exported reports.

MVP Focus
	•	Core Functionality:
Focus on:
	•	Script upload and basic PDF parsing
	•	Automated breakdown using Gemini 2.0
	•	Role-specific dashboards for key roles
	•	Basic collaboration tools (annotations, sharing)
	•	PDF and Excel export options
	•	Prioritization:
Emphasize core functionality over advanced features for the MVP.
	•	Gemini 2.0 Integration:
Ensure full integration and testing of the API as the MVP relies on it.
	•	Testing:
Perform thorough testing to ensure functionality for core features.

Deployment
	•	Deployment Setup:
Deploy the application to a suitable platform (e.g., Heroku, AWS, Google Cloud).
	•	Deployment Testing:
Fully test the deployed MVP before launch.

### Suggestions for Enhancing the MVP Instructions Document

#### **Setup Enhancements**
1. **Environment Isolation:**
   - Use virtual environments (e.g., `venv` or `conda` for Python and `nvm` for Node.js) to ensure dependencies are isolated.
   - Provide a `requirements.txt` file for Python dependencies and a `package.json` for JavaScript dependencies.

2. **Detailed Schema Definition:**
   - Include a basic schema diagram in the instructions to visualize the database structure.

**Conceptual Database Schema Diagram**

Here's a textual representation of the database relationships. Think of this as a simplified ER (Entity-Relationship) diagram:

```
-------------------      1         *   ------------------
|    scripts    | <---------------> |    scenes    |
-------------------                    ------------------
  script_id (PK)                      scene_id (PK)
  script_name                         script_id (FK)
  upload_date                         scene_number
  script_text                         setting
    user_id (FK)                         description
                                       characters
                                       props
                                       notes
-------------------                    ------------------
                                              |
                                              | 1
                                              |
-----------------       *              ---------------------
| director_notes | <--------------------|  scene  | --------
-----------------       1              ---------------------
| scene_id (FK) |                      scene_id (PK)
| scene_summary |                      
| emotional_beats|
| shot_suggestions|
-----------------                       ---------------------
                                              |
                                              | 1
                                              |
--------------------        *          --------------------
| producer_notes  | <--------------------| scene | ---------
--------------------        1          --------------------
| scene_id (FK)   |                     scene_id (PK)
| budget_estimation|
| scheduling_assistance|
| progress_tracking|
--------------------                    --------------------
                                               |
                                              | 1
                                               |
-----------------      *             --------------------
|  dop_notes     |<--------------------|   scene   | ---------
-----------------      1             --------------------
| scene_id (FK) |                    scene_id (PK)
| lighting_visual_cues|
| scene_analytics |
| equipment_needs |
-----------------                    --------------------
                                               |
                                               | 1
                                               |
-------------------------    *        --------------------
|production_designer_notes|<------------|   scene   | ---------
-------------------------    1        --------------------
| scene_id (FK)           |          scene_id (PK)
|set_dressing_requirements|
|props_and_wardrobe       |
|collaboration          |
-------------------------            --------------------
                                              |
                                              | 1
                                              |
-------------------     *          --------------------
|costume_designer_notes|<----------|   scene  | ---------
-------------------     1          --------------------
|scene_id (FK)       |           scene_id (PK)
|wardrobe_breakdown  |
|continuity_management|
-------------------                     --------------------
                                              |
                                              | 1
                                              |
---------------------      *      --------------------
| casting_director_notes |<--------|  scene | --------
---------------------      1      --------------------
|  scene_id (FK)        |         scene_id (PK)
|  character_breakdown  |
|  dialogue_analytics   |
---------------------            --------------------
                                             |
                                             | 1
                                             |
-------------------     *        --------------------
|location_manager_notes|<----------|   scene | --------
-------------------     1       --------------------
|scene_id (FK)          |        scene_id (PK)
|location_breakdown    |
|logistics_planning   |
-------------------                 --------------------
                                               |
                                               | 1
                                               |
------------------      *         ---------------------
|vfx_supervisor_notes|<-----------| scene | ---------
------------------      1         ---------------------
| scene_id (FK)       |          scene_id (PK)
| vfx_requirements    |
| budget_inputs      |
------------------                    ---------------------
                                              |
                                              | 1
                                              |
-------------------    *         ---------------------
|sound_department_notes|<--------|   scene  | ---------
-------------------     1        ---------------------
| scene_id (FK)       |         scene_id (PK)
| sound_breakdown     |
| music_cues          |
-------------------                    ---------------------
                                            |
                                            | 1
                                            |
-----------------     *           ---------------------
|makeup_and_hair_notes|<----------|  scene  | --------
-----------------     1           ---------------------
|scene_id (FK)       |            scene_id (PK)
|character_profiles   |
|scene_consistency    |
-----------------                   ---------------------
                                            |
                                            | 1
                                            |
------------------     *          ---------------------
|script_writer_notes|<----------|  scene   | --------
------------------     1        ---------------------
|scene_id (FK)        |           scene_id (PK)
|writer_notes       |
|version_history    |
------------------                  ---------------------
                                            |
                                            | 1
                                            |
------------------     *         ---------------------
|   actor_notes    | <----------|  scene   | --------
------------------     1          ---------------------
|scene_id (FK)       |            scene_id (PK)
|character_name    |
|actor_notes      |
|performance_notes |
------------------                   ---------------------

-----------------       *            ----------------
|    users    | <---------------> |  users_user_roles|
-----------------                    ----------------
  user_id (PK)                     user_id (FK)
  username                          role_id (FK)
  password                          (PK) user_id, role_id
  email
  first_name
  last_name
-----------------                    ----------------

-------------------     *     ----------------
| user_roles    | <--------------->  |users_user_roles |
-------------------                    ----------------
  role_id (PK)                         user_id (FK)
  role_name                         role_id (FK)
                                       (PK) user_id, role_id
-------------------                    ----------------
```

**Explanation:**

*   **Scripts Table:**
    *   `script_id`: Unique identifier for each script (Primary Key).
    *   `script_name`: Name of the script.
    *   `upload_date`: Timestamp when the script was uploaded.
    *   `script_text`: The full text of the parsed script.
       *   `user_id`: A foreign key referencing the `users` table, linking the script to a specific user.

*   **Scenes Table:**
    *   `scene_id`: Unique identifier for each scene (Primary Key).
    *   `script_id`: Foreign key referencing the `scripts` table, linking the scene to a specific script.
    *  `scene_number`: The scene number as identified in the script.
    *   `setting`: Description of the scene's location (e.g., "INT. KITCHEN - DAY").
    *   `description`: More detailed description of the scene.
    *   `characters`: List of characters in the scene.
    *   `props`: List of props needed in the scene.
    *   `notes`: Any additional notes for the scene.

*   **HOD Tables (director\_notes, producer\_notes, etc.):**
    *   Each table is dedicated to a specific Head of Department.
    *   They each contain a `scene_id` as a foreign key referencing the `scenes` table. This links these tables to a specific scene
    *   They contain various columns specific to their role (e.g., `shot_suggestions` for director\_notes, `budget_estimation` for producer\_notes).

*   **users Table:**
    *  `user_id`: Unique identifier for each user.
    * `username`: User's username
    * `password`: User's password
    * `email`: User's email
    * `first_name`: User's first name
    * `last_name`: User's last name

*   **user\_roles Table:**
   *  `role_id`: Unique identifier for each role.
    * `role_name`: Name of the role (e.g. Director, Producer, etc).

*  **users\_user\_roles Table:**
   * `user_id`: Foreign key relating to the users table
   * `role_id`: Foreign key relating to the user_roles table

**Key Relationships:**

*   **One-to-Many (1:N):**
    *   A `script` can have multiple `scenes`.
   *   A `scene` can have one `director_note`, `producer_note`, etc.
 *  A `user` can have many `users_user_roles`.
 *   A `user_role` can have many `users_user_roles`.

*   **Many-to-Many (N:N):**
    *   A `user` can have many roles
    *  A `role` can have many users.

**Important Notes:**

*   **JSONB:** I used `JSONB` as the data type for fields like `budget_estimation`, `scheduling_assistance`, `progress_tracking`, `character_breakdown`, and `dialogue_analytics`, which will help store structured data for those fields
*   **Foreign Keys (FK):** Foreign keys ensure referential integrity, meaning relationships are maintained correctly between related tables.
*   **Primary Keys (PK):** Primary keys ensure each row has a unique ID.
*   **Data Types:** The data types (e.g., `SERIAL`, `VARCHAR`, `TEXT`, `TIMESTAMP`, `JSONB`) are chosen to suit the data they will store. Adjust as per your database system.

   - Provide example SQL scripts for creating tables like `scripts`, `breakdown_data`, and `user_roles`.

3. **Secure API Keys:**
   - Recommend using a library like `python-decouple` or `dotenv` for environment variables.
   - Provide sample `.env` file templates for local development.

#### **Backend Development Suggestions**
1. **Scalable Parsing Workflow:**
   - Break parsing into smaller tasks that can be processed asynchronously (e.g., using Celery or a similar task queue).
   - Add support for additional file formats like Final Draft (.fdx) or Celtx as future scope.

2. **Error Logging:**
   - Use a centralized logging framework like `Loguru` (Python) or `Winston` (Node.js).
   - Define log levels (info, warning, error) and ensure API call failures or parsing errors are logged.

3. **Modular Role-Specific Data Structures:**
   - Provide example data structure definitions for each HOD role. For instance:
     ```python
     {
         "Director": {
             "scenes": [
                 {"scene_id": 1, "description": "INT. HOUSE - DAY", "characters": ["Alice", "Bob"]}
             ],
             "visual_notes": "Dim lighting required for emotional tone"
         },
         "Producer": {
             "budget_estimates": {"props": 2000, "wardrobe": 1000},
             "location_costs": [
                 {"location": "House", "cost": 3000}
             ]
         }
     }
     ```

4. **Enhanced API Design:**
   - Add endpoint documentation with sample input/output formats for `/upload_script` and `/get_breakdown_data`.
   - Use OpenAPI/Swagger for auto-generating API documentation.

#### **Frontend Development Suggestions**
1. **Design Systems:**
   - Use a design system (e.g., Material-UI, TailwindCSS) to speed up UI development and ensure consistency.

2. **Enhanced State Management:**
   - If the platform will grow, consider using Redux or Vuex instead of just Context API.

3. **Testing Frontend Components:**
   - Use tools like Jest and React Testing Library for unit testing frontend components.
   - Ensure all API integrations are mock-tested to handle varying backend responses.

4. **Collaborative Real-Time Updates:**
   - Implement basic WebSocket integration for real-time updates to annotations and comments.

#### **Collaboration Features Suggestions**
1. **Annotation Targeting:**
   - Allow annotations to target specific text lines or script elements by linking comments to a unique identifier.

2. **Permissions Management:**
   - Add user role-based permissions for tasks like viewing, commenting, or editing breakdown elements.

#### **Export Functionality Suggestions**
1. **Export Templates:**
   - Offer predefined templates for each HOD report but allow customization (e.g., drag-and-drop fields).

2. **Advanced File Options:**
   - Add options for exporting reports in additional formats like Google Sheets or Markdown for greater flexibility.

#### **Testing & Debugging**
1. **Automated Tests:**
   - Add automated tests for PDF parsing (e.g., parsing a diverse set of sample scripts with edge cases).

2. **Manual Testing Checklist:**
   - Provide a checklist for testing, e.g.,:
     - Upload success and error handling.
     - Correctness of extracted data (scenes, props, characters).
     - Frontend responsiveness on different devices.

3. **Performance Metrics:**
   - Define performance benchmarks for script processing time, dashboard load time, and API response times.

#### **General Recommendations**
1. **Iterative Feedback:**
   - Set up periodic feedback loops with early users to identify pain points and prioritize fixes or enhancements.

2. **Documentation:**
   - Provide inline comments in codebase.
   - Add developer-focused README sections, e.g., "How to set up local dev environment" and "How to deploy."

3. **Monitoring:**
   - Use a monitoring service like Sentry or New Relic to track errors and performance in the live environment.



