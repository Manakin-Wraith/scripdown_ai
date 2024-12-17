Okay, based on the provided information, here's a comprehensive project directory structure that incorporates both the backend (Flask) and frontend (React) components, along with the necessary configurations and documentation. This structure will help maintain clarity, organization, and scalability as the project grows.

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
│   │   ├── scene.py             # Scene model
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
│   │    ├── __init__.py
│   │   └── db_connection.py   # Database connection and configuration
│   ├── tests/                    # Backend unit tests
│   │    └── ...                   # tests here
│   ├── .env                      # Environment variables
│   └── requirements.txt          # Python dependencies

├── frontend/                     # Frontend application (React)
│   ├── src/
│   │   ├── components/          # Reusable UI components
│   │   │   ├── common/         # Common UI elements
│   │   │   │   ├── Button.js
│   │   │   │   ├── Input.js
│   │   │   │   ├── Modal.js
│   │   │   │   └── LoadingSpinner.js
│   │   │   ├── layout/         # Components to manage overall layout
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
│   │   │   │      ├── DirectorDashboard.js
│   │   │   │      ├── ProducerDashboard.js
│   │   │   │      ├── ProductionDesignerDashboard.js
│   │   │   │      └── ...other HOD dashboard components
│   │   │   └── auth/         # Authentication components
│   │   │       ├── LoginForm.js
│   │   │       └── SignUpForm.js
│   │   ├── containers/     # Components that manage state/logic and compose other components
│   │   │   ├── ScriptContainer.js
│   │   │   ├── DashboardContainer.js
│   │   │   └── AuthContainer.js
│   │   ├── pages/           # Top-level components for different routes
│   │   │   ├── HomePage.js
│   │   │   ├── ScriptPage.js
│   │   │   ├── AuthPage.js
│   │   │   └── NotFoundPage.js
│   │   ├── context/         # Context API components for global state
│   │   │   └── AuthContext.js
│   │   ├── services/       # Modules to handle API calls and business logic
│   │   │   ├── apiService.js
│   │   │   └── authService.js
│   │   ├── utils/             # Utility functions
│   │   │   └── helpers.js
│   │   ├── App.js
│   │   └── index.js
│   │   └── index.css
│   ├── public/               # Static assets
│   │   └── ...
│   ├── tests/                # Frontend unit tests
│   │   └── ...              # tests here
│   ├── .env                      # Environment variables
│   └── package.json              # Node.js dependencies

├── documentation/            # Project documentation
│   ├── api_docs.md             # API documentation
│   ├── database_schema.md      # Database schema details
│   └── ...

├── .gitignore                  # Git ignore file
└── README.md                   # Project README
```

**Explanation:**

**`script_breakdown/` (Root Directory):**

*   This is the main project folder that holds all the backend and frontend code.

**`backend/`:**

*   Contains all the backend-related code for the Flask application.
*   **`app.py`:** The main application file that initializes the Flask app.
*   **`config.py`:** Contains configuration settings.
*   **`routes/`:**
    *   **`script_routes.py`:** API routes for handling script uploads, parsing, and breakdown data retrieval.
    *   **`auth_routes.py`:** API routes for authentication and user management.
*   **`models/`:**
    *   **`script.py`:** Defines the `Script` model for the database.
    *   **`scene.py`:** Defines the `Scene` model for the database.
    *   **`hod_notes.py`:**  Defines all the HOD specific models.
    *   **`user.py`:** Defines the `User` model.
    *  **`user_roles.py`**: Defines the `UserRole` model and `user_user_roles` models
*   **`services/`:**
    *   **`script_service.py`:** Contains the main logic for processing scripts.
    *   **`gemini_service.py`:** Handles all the calls to the Gemini API.
    *    **`auth_service.py`:** Handles all authentication related service calls.
*  **`utils`:**
   *  **`pdf_parser.py`**: Contains the functionality to parse the uploaded PDF file
   *  **`auth_helper.py`**: Contains helper functions related to auth.
    *   **`error_handler.py`:** Handles errors and responses for the API.
*   **`db/`:**
    *   **`db_connection.py`:** Manages database connection logic.
*    **`tests/`:**
    *  Place for tests

*   **`.env`:** Environment variable file for backend.
*   **`requirements.txt`:** Lists all the Python dependencies for the backend.

**`frontend/`:**

*   Contains all the React-based frontend code.
*   **`src/`:** Holds all the source code for the app.
    *   **`components/`:** Holds all the reusable UI components
        *   **`common/`:**
             *  Contains generic UI components.
         *   **`layout/`**:
             *  Components to manage overall layout
         *    **`script_breakdown/`**:
             * Script breakdown specific components.
         *   **`auth/`**:
            *   Components related to authentication.
    *   **`containers/`:**  Components for handling state and logic and composing smaller components
    *   **`pages/`:** Top-level components for the different routes.
    *   **`context/`:** Context API for managing global state
    *   **`services/`:**
        *   **`apiService.js`:** Contains the functions for all the API calls
        *   **`authService.js`**: Functions for authentication related calls.
   *   **`utils/`**:
     *   **`helpers.js`**: Utility functions.
    *   **`App.js`**: Main app component.
    *   **`index.js`**: Entry point of the app.
    *  **`index.css`**: CSS file for the app.
*   **`public/`:** Holds static assets like images, logos, etc.
*   **`tests/`**:
   * Place for all the test files
*  **`.env`**: Environment variables for the frontend.
*   **`package.json`:** Lists all the Node.js dependencies for the frontend.

**`documentation/`:**

*   Contains all documentation for the project.
*   **`api_docs.md`:** Provides details about the different endpoints in the API.
*   **`database_schema.md`:** Detailed description of the database schema.

**Root Level Files:**

*   **`.gitignore`:** Specifies intentionally untracked files that Git should ignore.
*   **`README.md`:** Provides an overview of the project, instructions for setting up and running, and more.

**Key Points:**

*   **Modularity:** The structure promotes modularity, making the codebase easy to navigate and maintain.
*   **Scalability:** Designed to handle additional features and complexity in the future.
*   **Separation of Concerns:** Separates frontend, backend, and documentation, enhancing clarity.
*   **Naming Conventions:** Follow clear and consistent naming conventions for files and directories.

This detailed directory structure should give you a solid foundation for your project, enabling organized and efficient development of the ScriptDown MVP.
