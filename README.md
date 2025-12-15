# EDP4E-AI-CHATBOT

### 1\. Core Functionality

The EDP4E-AI-CHATBOT acts as an intelligent intermediary, transforming complex user questions (like "What is the current stock of part X?") into structured database queries.

| Feature | Description |
| :--- | :--- |
| **Input** | Natural Language Question (via the HTML text area). |
| **Processing** | An AI component (likely in `app.py`) analyzes the text, generates a SPARQL query, and executes it against the Knowledge Graph endpoint. |
| **Output** | The chat interface provides a user-friendly response, while the "Technical Details" section displays the generated SPARQL query and the raw JSON results from the graph database. |
| **Domain** | Vehicle component data, potentially linked to **Supply Chain & Inventory Optimization** (predicting shortages, sourcing strategies, etc.). |

### 2\. File Contents and Responsibilities

The application consists of three primary files: one for the server logic (`app.py`), one for the user interface (`index.html`), and one for styling (`styles.css`).

| File Name | Role | Contains |
| :--- | :--- | :--- |
| `app.py` | **Backend Server / Core Logic** | \* **Flask Server Setup:** Defines routes (e.g., `/query`).<br>\* **AI Integration:** Code to call the NLP/LLM service (e.g., Gemini API, or similar) to generate SPARQL.<br>\* **SPARQL Execution:** Logic to send the generated SPARQL query to the Knowledge Graph endpoint (e.g., Fuseki).<br>\* **Response Handling:** Processes the Fuseki results and formats them for the frontend. |
| `index.html` | **Frontend / User Interface** | \* **HTML Structure:** The main layout, including the chat area (`#chatbot-interface`), the input form (`#form`), and the technical display sections (`#sparql`, `#results`).<br>\* **JavaScript (`<script>`):** Handles user interaction (form submission, AJAX calls to `app.py/query`), dynamic chat message display, textarea resizing, and error handling. |
| `styles.css` | **Visual Presentation** | \* **Styling:** All CSS rules defining the visual theme, layout, colors, fonts, and responsive behavior for the HTML elements, including the chat bubbles, input area, and code blocks. |

### 3\. Key Components and Technologies

  * **Flask:** The lightweight Python web framework powering the backend.
  * **AI/NLP:** Used for the crucial **Natural Language to SPARQL** transformation.
  * **Knowledge Graph (KG):** The underlying database (like Fuseki) queried by SPARQL, containing the structured data about JLR parts and supply chain information.
  * **AJAX (in JS):** Enables the non-blocking communication between the HTML frontend and the Python backend (`app.py`).

