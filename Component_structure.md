**Component Structure Overview**

The core idea is to break down the UI into smaller, manageable pieces. This structure assumes a SPA (Single-Page Application) architecture:

```
src/
├── components/          # Reusable UI components
│   ├── common/         # Common UI elements (e.g., buttons, inputs, modals)
│   │   ├── Button.js
│   │   ├── Input.js
│   │   ├── Modal.js
│   │   └── LoadingSpinner.js
│   ├── layout/         # Components to manage overall layout
│   │   ├── Header.js
│   │   ├── Sidebar.js
│   │   └── Footer.js
│   ├── script_breakdown/ # Components related to the script breakdown process
│   │   ├── ScriptUpload.js #handles file uploads
│   │   ├── SceneSummary.js #displays scene summary
│   │   ├── BreakdownTable.js #displays data in a table
│   │   ├── RoleDashboard.js #displays a single role based dashboard
│   │   ├── BreakdownComment.js #displays and handles comments
│   │   └── HOD_components/ # specific hod components
│   │    ├── DirectorDashboard.js
│   │    ├── ProducerDashboard.js
│   │    ├── ProductionDesignerDashboard.js
│   │    └── ...other HOD dashboard components
│   └── auth/         # Components for user authentication
│       ├── LoginForm.js
│       └── SignUpForm.js
├── containers/     # Components that handle state/logic and compose other components
│   ├── ScriptContainer.js  #Handles script logic, state
│   ├── DashboardContainer.js # Handles dashboard logic and state
│   └── AuthContainer.js # Handles user authentication and related logic
├── pages/           # Top-level components for different routes
│   ├── HomePage.js # Main dashboard
│   ├── ScriptPage.js  # Page to upload and view script breakdown
│   ├── AuthPage.js # page to display authentication forms
│   └── NotFoundPage.js # Page not found
├── context/         # Context API components for global state
│   └── AuthContext.js
├── services/       # Modules to handle API calls and business logic
│   ├── apiService.js #handles API calls to backend
│   └── authService.js #Handles authentication service calls
├── utils/             # Utility functions
│   └── helpers.js #helper functions
├──App.js
├──index.js
└──...other files

```

**Component Descriptions:**

*   **`components/`**
    *   `common/`: Generic UI components that are used across the application.
        *   `Button.js`, `Input.js`, `Modal.js`: Common form elements, buttons, and modals.
        *   `LoadingSpinner.js`: A component to indicate loading states.
    *   `layout/`: Components that define the overall page structure.
        *   `Header.js`, `Sidebar.js`, `Footer.js`: Components to handle header, sidebar, and footer functionality.
    *   `script_breakdown/`: Specific components for handling script-related features.
        *   `ScriptUpload.js`: Handles script upload functionality.
        *   `SceneSummary.js`: Displays a scene summary.
        *   `BreakdownTable.js`: Generic component to display extracted data in a table format.
        *   `RoleDashboard.js`: Displays a dashboard for a single role
         *   `BreakdownComment.js`: Displays and handles comments
         *  `HOD_components/`: Specific components for each Head of Department dashboards
              * `DirectorDashboard.js`: Dashboard for the director role
              * `ProducerDashboard.js`: Dashboard for the producer role
              * `ProductionDesignerDashboard.js`: Dashboard for production designer role
             * ... other dashboard components
    *  `auth`: Components to handle authentication functionality
        *`LoginForm.js`: Handles user login
       *`SignUpForm.js`: Handles user signup

*   **`containers/`**
    *   These components handle state management, API calls, and business logic. They orchestrate other presentational components.
        *   `ScriptContainer.js`: Handles the state and logic for uploading scripts and getting script breakdown data.
        *   `DashboardContainer.js`: Handles fetching of relevant dashboard data.
          *   `AuthContainer.js`: Handles the state and logic of authentication components.

*   **`pages/`**
    *   Top-level components that represent different routes or views of the app.
        *   `HomePage.js`: Main dashboard view.
        *   `ScriptPage.js`: Page for uploading and viewing script breakdowns.
        *   `AuthPage.js`: Page for logging in or signing up.
        *   `NotFoundPage.js`: Page to display for invalid URLs.
*  **`context`**
    * Components that handle global state functionality
      *  `AuthContext.js`: Context api for storing auth related state

*   **`services/`**
    *   Modules to handle API calls and business logic.
        *   `apiService.js`: Functions for making API calls to your backend.
        *  `authService.js`: Functions for authentication related service calls

*   **`utils/`**
    *   Utility functions that are not specific to any component.
       *   `helpers.js`: Helper functions

* **`App.js`**
  *The main app component that sets up the app router.

* **`index.js`**
 * Entry point of the application

**Detailed Component Usage**

1.  **`ScriptUpload.js`**
    *   Handles the UI for file uploads using a standard HTML `<input type="file" />` element.
    *   Sends file to `/upload_script` API endpoint in the backend (likely via the `apiService`).
    *   Manages loading state during upload using LoadingSpinner.js
2.  **`BreakdownTable.js`**
    *   Takes data as props and renders it in a structured HTML table using `<th>` and `<td>` elements.
    *   A generic component to be used in different `HOD_dashboard` components.

3.  **`RoleDashboard.js`**
    *   Handles the functionality for a single dashboard
    *   Displays data by using the `BreakdownTable.js` component, or by using individual components for a specific role
    *  Fetches data from the `/get_breakdown_data` endpoint using the `apiService` based on the `script_id` and the `role` passed to it as a prop

4.  **HOD Specific Dashboard Components(`DirectorDashboard.js`,`ProducerDashboard.js`, etc.)**
   *  These components use the `RoleDashboard.js` to display data for a particular role
    *   Passes `role` as a prop to `RoleDashboard.js` component.

5.  **`SceneSummary.js`**
    *   Takes a scene summary as a prop.
    *   Displays the summary using HTML elements such as paragraphs.

6.  **`BreakdownComment.js`**
    * Displays the comments relevant to a scene.
    * Provides functionality to add new comments
    *  Uses `apiService` to create and fetch comments

7.   **`ScriptContainer.js`**
    *   Manages the script upload process, state.
    *   Gets data from the backend via `/get_breakdown_data` endpoint.
    *  Passes required data to child components such as `RoleDashboard`.

8.  **`DashboardContainer.js`**
    *   Handles the navigation to the required dashboards
    *  Gets all relevant dashboard data and passes to the dashboards as a prop.

9. **`AuthContainer.js`**
  *  Manages the authentication and related state
   * Gets data from the `authService.js`
   * Passes data to child components such as `LoginForm.js` and `SignUpForm.js`

10.  **`apiService.js`**
    *   Contains functions that communicate with the API endpoints created on the backend using `fetch` or a similar library.
    *  Includes all `POST`, `GET` calls made from the application.

11. **`authService.js`**
    * Handles the functionality for login, signup and authentication
    * Calls the backend authentication APIs, handles tokens

**Implementation Notes**

*   **State Management:**  Use React's built-in state management (`useState`, `useContext`), or a state management library (e.g., Redux, Zustand, Recoil) if required.
*   **Props:** Use props to pass data between components.
*   **Component Composition:**  Build larger components by composing smaller components (e.g., building a page from layout components and `script_breakdown` components).
*   **Styling:** Use CSS modules, styled-components, or a CSS framework (e.g., Tailwind CSS, Bootstrap) for styling.
*   **Routing:** Use a routing library (e.g., React Router) for handling navigation between pages.


