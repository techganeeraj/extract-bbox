# 📄  Document Intelligence  - Bounding Box Extractor

This project is a Python Flask application that leverages the powerful **Gemini 3 Pro** model on Google Cloud's Vertex AI for advanced Document Intelligence (DI). It is specifically designed to extract highly structured line-item data, financial details, and normalized bounding box coordinates from uploaded PDF documents.

The application supports both a command-line interface (CLI) for quick testing and a web API for integration.

## ✨ Features

*   **Gemini 3 Pro Power:** Utilizes the advanced Gemini 3 Pro model for complex document reasoning and information extraction.
*   **Structured Line-Item Extraction:** Extracts detailed line-item data (e.g., service dates, item codes, quantity, price, discounts, total amounts) often found in invoices, medical bills, or financial statements.
*   **Normalized Bounding Boxes (BBoxes):** Returns precise bounding box coordinates for both field **labels** and **values**, normalized to a scale of **0-1000** for easy mapping back to the document image/canvas.
*   **Strict JSON Schema Output:** The model's response is strictly enforced to follow a predefined JSON schema, ensuring consistent and predictable data output.
*   **Dual Mode Operation:** Can be run as a standalone CLI tool or as a RESTful Flask web service.
*   **PDF Processing:** Optimized for handling PDF documents (`.pdf` files).

## 🛠️ Setup and Installation

### Prerequisites

1.  **Python 3.8+**
2.  **Google Cloud Project:** A Google Cloud project with the **Vertex AI API** enabled.
3.  **Authentication:** You must be authenticated to use the Vertex AI client. This is typically done using [Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/provide-credentials-adc) for local development:
    ```bash
    gcloud auth application-default login
    ```

### 1. Clone the repository (Assuming the code is in a file named `app.py`)

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

**`requirements.txt` contents:**

```
Flask
google-genai
werkzeug
```

## ⚙️ Configuration

The application is hard-coded with specific Google Cloud settings within the `generate` function. **You must change these values.**

### Vertex AI Client Configuration

Modify the following lines in the `generate` function:

```python
  client = genai.Client(
      vertexai=True,
      project="ng-project-102",  # <-- CHANGE THIS to YOUR GCP Project ID
      location="global",         # <-- CHANGE THIS if your model is not in 'global'
  )

  model = "gemini-3-pro-preview" # Ensure this model is available in your location
```

## 🚀 Usage

The application supports two modes: CLI and Web API.

### A. Command Line Interface (CLI) Mode

For quick testing or processing a single file without running the web server.

```bash
python app.py <path/to/your/document.pdf>
```

**Example:**

```bash
python app.py ./invoices/sample_bill.pdf
```

The structured JSON output will be printed directly to the console.

### B. Web API (Flask) Mode

For a persistent, accessible service.

#### 1. Run the Web Server

```bash
python app.py
# Running on http://127.0.0.1:8000/ (Press CTRL+C to quit)
```

#### 2. API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Renders the frontend HTML page (`index.html` - **not provided**). |
| `/upload` | `POST` | The main extraction endpoint. Uploads a PDF file for processing. |

#### 3. Calling the `/upload` Endpoint (Using `curl`)

Send a `multipart/form-data` request with the PDF file under the field name `file`.

```bash
curl -X POST http://localhost:8000/upload \
     -F 'file=@/path/to/your/document.pdf'
```

**Successful Response Example:**

Returns a JSON object matching the defined schema, containing line-item details with extracted values and bounding box coordinates.

```json
{
    "line_details1": [
        {
            "claimId": { "value": "", "labelBbox": [0, 0, 0, 0], "valueBbox": [0, 0, 0, 0] },
            "serviceDateTime": { "value": "08-15-2023", "labelBbox": [45, 100, 55, 150], "valueBbox": [234, 156, 250, 190] },
            "itemCode": { "value": "A123", "labelBbox": [45, 300, 55, 350], "valueBbox": [234, 310, 250, 350] },
            // ... all other fields
        }
        // ... subsequent line items
    ]
}
```

## 📝 Important Notes

*   **File Type Limit:** The API is configured to only allow **PDF files**.
*   **Temporary Files:** Uploaded files are saved to a temporary directory (`tempfile.gettempdir()`), processed, and **immediately deleted** after the analysis is complete, ensuring good resource management.
*   **Max File Size:** The application is configured to accept a maximum file size of **16MB** (`app.config['MAX_CONTENT_LENGTH']`).
