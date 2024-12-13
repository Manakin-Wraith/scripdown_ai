Okay, based on the database schema and the described MVP functionality, here's a breakdown of API endpoints, including their methods, purposes, and expected request/response structures. I'll use a RESTful approach and assume you're using Flask or a similar framework.

**Assumptions:**

*   You have a Flask application set up.
*   You have a database connection established.
*   You have functions to parse the PDF and interact with the Gemini 2.0 API (we'll assume these exist).
*   You are using the database structure as previously defined
*   You have some form of user authentication middleware to make sure users are valid

**Endpoint 1: `/upload_script` (POST)**

This endpoint handles the upload of a PDF script, parses it, interacts with the AI, and stores the results.

```python
from flask import Flask, request, jsonify
import os
from werkzeug.utils import secure_filename
#Assuming there is a function called "process_script" that handles the script parsing, AI processing and data storage.
from your_module import process_script

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads' # Directory to save the uploaded files
ALLOWED_EXTENSIONS = {'pdf'} # Set the allowed file types
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#Helper function
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload_script', methods=['POST'])
def upload_script():
    # Check if the user is authenticated
    if not user_is_authenticated():
        return jsonify({'message': 'Unauthorized access'}), 401


    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['file']

    # Check if file is selected
    if file.filename == '':
       return jsonify({'message': 'No file selected'}), 400

    # Check the file extension
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            script_id= process_script(file_path) # assuming process_script now also returns a script_id
            return jsonify({'message': 'Script processed successfully', "script_id": script_id}), 201
        except Exception as e:
            return jsonify({'message': f'Error processing script: {str(e)}'}), 500
    else:
        return jsonify({'message': 'Invalid file type. Only PDF is allowed'}), 400

#Helper user authentication function
def user_is_authenticated():
    #Add your authentication implementation here
    # This is for example purposes and does not do any real authentication
    # e.g You might validate a token, session, or some other authentication
    return True

if __name__ == '__main__':
    #Create folder if it does not exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
```

**Explanation:**

1.  **Imports:** Import necessary Flask modules, `os` for file handling, and `secure_filename` for security.
2.  **Setup:**
    *   Set the upload folder and allowed file extensions.
    *   Define `allowed_file` function to validate the file extension.
3.  **`/upload_script` Route:**
    *   Handles `POST` requests.
    *   Validates that a file is present in the request.
    *   Ensures the file type is PDF.
    *   Saves the uploaded file securely.
    *   Calls `process_script()` function which would ideally take the filepath, extract the text, sends the data to Gemini, stores the extracted data in the database, and would return the script\_id
    *   Returns a success message and the generated `script_id` or an error message.
4.  **Error Handling:** Includes basic error handling for file uploads and processing.
5. **Authentication**: Includes a basic authentication middleware

**Endpoint 2: `/get_breakdown_data` (GET)**

This endpoint fetches the breakdown data based on the role provided in the request parameters.

```python
from flask import Flask, request, jsonify
import psycopg2  # Or your database connector library
from your_module import get_database_connection # assuming this will return a database cursor
app = Flask(__name__)
# A helper function to determine table name based on the role
def get_table_name(role):
    role_table_mapping = {
        'Director': 'director_notes',
        'Producer': 'producer_notes',
        'DoP': 'dop_notes',
        'Production_Designer': 'production_designer_notes',
        'Costume_Designer': 'costume_designer_notes',
        'Casting_Director': 'casting_director_notes',
        'Location_Manager': 'location_manager_notes',
        'VFX_Supervisor': 'vfx_supervisor_notes',
        'Sound_Department': 'sound_department_notes',
        'Makeup_and_Hair': 'makeup_and_hair_notes',
        'Script_Writer':'script_writer_notes',
        'Actor':'actor_notes'
    }
    return role_table_mapping.get(role)
@app.route('/get_breakdown_data', methods=['GET'])
def get_breakdown_data():
    # Check if the user is authenticated
    if not user_is_authenticated():
        return jsonify({'message': 'Unauthorized access'}), 401


    script_id = request.args.get('script_id', type=int)
    role = request.args.get('role')


    if not script_id:
       return jsonify({'message':'No script id provided'}), 400

    if not role:
      return jsonify({'message':'No role provided'}), 400


    table_name = get_table_name(role)
    if not table_name:
       return jsonify({'message': 'Invalid role'}), 400

    conn = None
    try:
        conn= get_database_connection() # returns a cursor connection
        cur = conn.cursor()
        if table_name in ['script_writer_notes', 'actor_notes']: #if the role is script writer or actor we need to grab data from scenes
           cur.execute(f'''SELECT scenes.scene_number, scenes.setting, scenes.description, {table_name}.*
                                FROM scenes
                                INNER JOIN {table_name} ON scenes.scene_id = {table_name}.scene_id
                                WHERE scenes.script_id = %s''', (script_id,))
        else:
            cur.execute(f'''SELECT scenes.scene_number, scenes.setting, scenes.description, {table_name}.*
                                FROM scenes
                                INNER JOIN {table_name} ON scenes.scene_id = {table_name}.scene_id
                                WHERE scenes.script_id = %s''', (script_id,))
        results = cur.fetchall()

        if not results:
            return jsonify({'message': f'No data found for {role} and script_id:{script_id}'}), 404

        # Convert results to a list of dictionaries for easier JSON serialization
        columns = [col[0] for col in cur.description] #gets the column names
        data = [dict(zip(columns, row)) for row in results] #converts to a dictionary

        return jsonify(data), 200

    except Exception as e:
        return jsonify({'message': f'Error fetching breakdown data: {str(e)}'}), 500
    finally:
      if conn:
        cur.close()
        conn.close()


#Helper user authentication function
def user_is_authenticated():
    #Add your authentication implementation here
    # This is for example purposes and does not do any real authentication
    # e.g You might validate a token, session, or some other authentication
    return True
if __name__ == '__main__':
    app.run(debug=True)
```

**Explanation:**

1.  **Imports:** Import necessary Flask modules, your database connector, and helper functions.
2.  **`get_table_name` Function:** Defines a mapping of the HOD role names and their respective tables.
3.  **`/get_breakdown_data` Route:**
    *   Handles `GET` requests.
    *   Retrieves the `script_id` and `role` from the query parameters.
    *   Validates that both parameters are present.
    *   Uses the `get_table_name` function to retrieve the correct table name.
    *   Queries the database for data related to that role, also grabbing the scene number, setting and description from the scenes table.
    *   Returns the results in JSON format or returns an error if no data is found
4. **Error handling**: Includes basic error handling for API calls, and data retrieval
5. **Authentication**: Includes a basic authentication middleware

**Important Notes:**

*   **Database Interaction:** The SQL queries are examples. You should adjust these to match your specific needs and the structure of your database.
*   **Error Handling:** The error handling is basic. Consider adding more robust logging and error responses for production environments.
*   **Database Connection:** Assume the function `get_database_connection` exists to connect to your database.
*  **Authentication:** Add your authentication middleware to make sure users are valid.
*   **Security:** Implement proper authorization for API access, based on the user's role.
*   **Helper Functions:** Your application should include the mentioned  `process_script` function, as well as a function that returns a database cursor `get_database_connection` function.

These are the basic building blocks for the API endpoints. You can extend these with additional features, such as pagination, search, more detailed error messages, etc.


**API Endpoints:**

1.  **Script Management**

    *   `POST /scripts`
        *   **Purpose:** Upload a new script (PDF).
        *   **Request Body:** `multipart/form-data` with a `file` (the PDF) and `script_name`.
          ```json
           {
               "script_name": "My Script Title"
            }
         ```
        *   **Response (Success - 201 Created):**
            ```json
            {
                "message": "Script uploaded and processing started.",
                "script_id": 123 // The id of the created script
             }
            ```
        *   **Response (Error - 400 Bad Request):**
            ```json
             {
                 "error": "Invalid file format or missing data."
              }
            ```
        *   **Response (Error - 500 Internal Error):**
           ```json
              {
                 "error": "Internal error. Please try again later."
              }
           ```
    *   `GET /scripts`
        *   **Purpose:** Get all scripts uploaded by the user.
        *   **Response (Success - 200 OK):**
            ```json
            [
                {
                    "script_id": 1,
                    "script_name": "My Script Title",
                     "upload_date": "2024-10-27T12:00:00"
                },
              {
                    "script_id": 2,
                    "script_name": "Another Script Title",
                     "upload_date": "2024-10-27T14:00:00"
                }
            ]
            ```
    *   `GET /scripts/{script_id}`
        *   **Purpose:** Get a specific script by its ID.
        *  **Request Params:** `script_id`
        *   **Response (Success - 200 OK):**
            ```json
               {
                    "script_id": 123,
                    "script_name": "My Script Title",
                    "upload_date": "2024-10-27T12:00:00",
                    "script_text":"the full text of the script"

                }
            ```
       *   **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Script not found."
              }
            ```

2.  **Scene Management**

    *   `GET /scripts/{script_id}/scenes`
        *   **Purpose:** Get all scenes for a specific script
          * **Request Params:** `script_id`
        *   **Response (Success - 200 OK):**
            ```json
            [
                {
                    "scene_id": 1,
                     "scene_number": 1,
                     "setting": "INT. KITCHEN - DAY",
                     "description": "Emily is making breakfast",
                       "characters": ["Emily", "Tom"],
                       "props": ["plates", "forks"],
                     "notes":"some note"
                 },
                {
                    "scene_id": 2,
                      "scene_number": 2,
                    "setting": "EXT. PARK - DAY",
                     "description": "Tom is running",
                        "characters": ["Tom"],
                     "props": ["sports clothes"],
                        "notes":"some other note"

                }
            ]
            ```

    *    `GET /scenes/{scene_id}`
        *   **Purpose:** Get a specific scene by it's ID.
         * **Request Params:** `scene_id`
        *   **Response (Success - 200 OK):**
            ```json
              {
                    "scene_id": 1,
                     "scene_number": 1,
                     "setting": "INT. KITCHEN - DAY",
                     "description": "Emily is making breakfast",
                       "characters": ["Emily", "Tom"],
                       "props": ["plates", "forks"],
                     "notes":"some note"

                }
            ```
      *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Scene not found."
              }
            ```

3.  **Role-Based Data Retrieval**

    *   `GET /scenes/{scene_id}/director-notes`
        *   **Purpose:** Get director-specific notes for a scene.
        *  **Request Params:** `scene_id`
        *   **Response (Success - 200 OK):**
            ```json
               {
                    "scene_id": 1,
                    "scene_summary": "Emily is making breakfast",
                    "emotional_beats": "Warmth and domestic bliss",
                    "shot_suggestions": "Close-up of the food preparation"
                 }
            ```
         *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```

    *   `GET /scenes/{scene_id}/producer-notes`
        *   **Purpose:** Get producer-specific notes for a scene.
          *  **Request Params:** `scene_id`
        *   **Response (Success - 200 OK):**
            ```json
               {
                 "scene_id":1,
                  "budget_estimation": {
                      "location": "Kitchen Set",
                      "props": "plates, forks",
                      "wardrobe": "casual clothes"
                      },
                    "scheduling_assistance": {
                         "location_type": "interior",
                        "actor_availability": ["Emily", "Tom"],
                          "estimated_time": "2 hours"
                     },
                       "progress_tracking": {
                          "breakdown_status": "complete",
                          "team_contributions": {
                                "director": "notes added",
                                 "producer": "notes added",
                                "production_designer": "To do"
                          }
                       }
                 }
            ```
        *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```

    *   `GET /scenes/{scene_id}/dop-notes`
        *   **Purpose:** Get DoP-specific notes for a scene.
          *  **Request Params:** `scene_id`
        *   **Response (Success - 200 OK):**
           ```json
               {
                     "scene_id":1,
                    "lighting_visual_cues": "Soft morning light",
                   "scene_analytics": "Simple setup",
                    "equipment_needs": "Camera, tripod"
                 }
             ```
        *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```

    *   `GET /scenes/{scene_id}/production-designer-notes`
        *   **Purpose:** Get production designer-specific notes for a scene.
          *  **Request Params:** `scene_id`
        *   **Response (Success - 200 OK):**
          ```json
              {
                   "scene_id":1,
                    "set_dressing_requirements": "kitchen utensils, plates",
                    "props_and_wardrobe": "forks, bowls, everyday clothes",
                     "collaboration": "ensure plates match other scenes"
                  }
            ```
        *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```

    *  `GET /scenes/{scene_id}/costume-designer-notes`
        *   **Purpose:** Get costume designer-specific notes for a scene.
          *  **Request Params:** `scene_id`
        *   **Response (Success - 200 OK):**
           ```json
             {
                   "scene_id":1,
                 "wardrobe_breakdown": "casual clothing",
                  "continuity_management": "ensure Emily has same clothes as prior scene"

            }
            ```
        *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```
    *   `GET /scenes/{scene_id}/casting-director-notes`
         *   **Purpose:** Get casting director-specific notes for a scene.
          *  **Request Params:** `scene_id`
        *  **Response (Success - 200 OK):**
            ```json
             {
                   "scene_id":1,
                   "character_breakdown": [
                        {
                            "character_name": "Emily",
                            "role_type": "speaking",
                             "importance": "main"
                        },
                        {
                          "character_name": "Tom",
                            "role_type": "speaking",
                             "importance": "main"
                        }
                    ],
                     "dialogue_analytics": {
                      "Emily_dialogue": "significant dialogue",
                       "Tom_dialogue": "some lines"
                      }
                 }
            ```
        *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```
    * `GET /scenes/{scene_id}/location-manager-notes`
         *   **Purpose:** Get location manager-specific notes for a scene.
          *  **Request Params:** `scene_id`
        * **Response (Success - 200 OK):**
             ```json
              {
                  "scene_id":1,
                 "location_breakdown": "interior of a typical house kitchen",
                 "logistics_planning": "ensure kitchen is available for the required shoot dates"
              }
              ```
       *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```

    *  `GET /scenes/{scene_id}/vfx-supervisor-notes`
        *   **Purpose:** Get VFX supervisor-specific notes for a scene.
          *  **Request Params:** `scene_id`
        *  **Response (Success - 200 OK):**
            ```json
              {
                    "scene_id": 1,
                     "vfx_requirements": "add a subtle background effect",
                     "budget_inputs": "low budget required"
                }
            ```
       *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```
    *  `GET /scenes/{scene_id}/sound-department-notes`
         *   **Purpose:** Get Sound department-specific notes for a scene.
          *  **Request Params:** `scene_id`
        * **Response (Success - 200 OK):**
             ```json
              {
                   "scene_id": 1,
                   "sound_breakdown": "kitchen sounds, breakfast sounds",
                    "music_cues": "light background music"
                }
              ```
      *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```
   *    `GET /scenes/{scene_id}/makeup-and-hair-notes`
        *   **Purpose:** Get makeup and hair-specific notes for a scene.
          *  **Request Params:** `scene_id`
        *   **Response (Success - 200 OK):**
            ```json
            {
                   "scene_id": 1,
                  "character_profiles": "basic day make up and hair for all characters",
                  "scene_consistency": "Emily must have same hair and make up as previous scenes"
            }
            ```
        *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```
     *    `GET /scenes/{scene_id}/script-writer-notes`
        *   **Purpose:** Get script writer-specific notes for a scene.
          *  **Request Params:** `scene_id`
        *   **Response (Success - 200 OK):**
            ```json
            {
                   "scene_id": 1,
                  "writer_notes": "ensure continuity with the previous scene",
                   "version_history": [{"date":"2024-10-27", "note":"minor edit to scene"}]
            }
            ```
         *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```
       *    `GET /scenes/{scene_id}/actor-notes`
        *   **Purpose:** Get actor-specific notes for a scene.
          *  **Request Params:** `scene_id`
        *   **Response (Success - 200 OK):**
            ```json
            {
                   "scene_id": 1,
                     "character_name": "Emily",
                     "actor_notes": "focus on calmness",
                     "performance_notes": "must play as if she is not upset"
            }
            ```
         *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "Notes not found."
              }
            ```

4.  **User and Role Management (Basic)**

    *   `POST /users`
        *   **Purpose:** Create a new user (for registration).
        *   **Request Body:**
            ```json
                {
                    "username": "newuser",
                    "password": "password123",
                    "email": "newuser@email.com",
                      "first_name": "John",
                    "last_name": "Doe"
                }
            ```
        *   **Response (Success - 201 Created):**
            ```json
            {
              "message": "User created successfully",
                 "user_id": 123
           }
            ```
    *   `POST /users/login`
          *   **Purpose:** login an existing user
        *   **Request Body:**
          ```json
                {
                    "username": "existinguser",
                    "password": "password123"
                  }
          ```
      * **Response (Success - 200 OK):**
             ```json
            {
               "message": "User logged in successfully"
           }
            ```

    *  `GET /users/roles`
        *  **Purpose:** get all user roles
        *  **Response (Success - 200 OK):**
             ```json
                 [
                    { "role_id": 1, "role_name": "Director"},
                    { "role_id": 2, "role_name": "Producer"}
                  ]
              ```
    *  `PUT /users/{user_id}/roles`
        *  **Purpose:** set a users role
        *  **Request Params:** `user_id`
          * **Request Body:**
          ```json
                {
                   "role_ids":[1,2] // A list of role ids
                 }
          ```
      * **Response (Success - 200 OK):**
             ```json
            {
               "message": "User roles updated successfully"
           }
           ```
       *  **Response (Error - 404 Not Found):**
            ```json
              {
                "error": "User not found."
              }
            ```

**Important Considerations:**

*   **Error Handling:** Implement proper error handling and provide meaningful error messages to the frontend.
*   **Authentication/Authorization:** Implement secure authentication and authorization mechanisms to protect your API.
*   **Rate Limiting:** Consider rate limiting to prevent abuse of your API.
*   **Data Validation:** Validate all incoming data to avoid database errors.
*   **Pagination:** For GET requests that might return large datasets (e.g., `/scripts`), implement pagination.

This detailed API endpoint list should provide a solid foundation for your MVP. Remember to adjust it based on your specific needs and chosen technology stack.
