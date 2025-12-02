import argparse
import mimetypes
from google import genai
from google.genai import types
import os
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
import json
import tempfile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate(file_path):
  """
  Generates content from a given file using the Gemini model.

  Args:
      file_path (str): The path to the image or PDF file.
  Returns:
      str: JSON string containing the extracted tags
  """
  client = genai.Client(
      vertexai=True,
      project="ng-project-102",
      location="global",
  )

  # Infer the MIME type of the file
  mime_type, _ = mimetypes.guess_type(file_path)
  if mime_type is None:
      # Fallback for unknown types, or be more specific if needed
      if file_path.lower().endswith('.pdf'):
          mime_type = 'application/pdf'
      else:
        raise ValueError("Could not determine the MIME type of the file.")

  with open(file_path, "rb") as f:
      file_bytes = f.read()

  file_part = types.Part.from_bytes(
      data=file_bytes,
      mime_type=mime_type,
  )

  model = "gemini-3-pro-preview"
  contents = [
    types.Content(
      role="user",
      parts=[
        types.Part.from_text(text="""Identify the tags and extract bounding box coordinates for both labels and values. 
For each extracted field, provide normalized bounding box coordinates in the format [y_min, x_min, y_max, x_max] 
where coordinates are normalized to a scale of 0-1000 (multiply actual coordinates by 1000 and divide by document dimensions).
Extract bounding boxes for both the field label (if visible) and the field value. 
If a label is not visible on the document, return empty bounding box [0, 0, 0, 0] for the label.
Always provide bounding box coordinates for values when they exist."""),
        file_part
      ]
    )
  ]

  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 1,
    max_output_tokens = 65535,
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    response_mime_type = "application/json",
    response_schema = {
        "type": "object",
        "properties": {
            "line_details1": {
                "type": "array",
                "description": "Contains a list of line item details. Include total and subtotal rows as well.",
                "items": {
                    "type": "object",
                    "properties": {
                        "claimId": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Return an empty string."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "lineId": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Return an empty string."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "serviceDateTime": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract the 'Reference Date', 'service date', 'Registry Rate' or any Date mentioned in MM-DD-YYYY format. If these values are present within the line item, extract them from the line item. If these values are not present within the line item, extract them from the header section. If the current row is an 'ITEM' row, return the extracted 'service date'. If the current row is a 'SECTION TOTAL' or 'TOTAL' row, return an empty string for 'service date'."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "itemCode": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract ONLY the value corresponding to 'Item Code' or 'Item ID', ONLY IF the KEY exists on the document. UNMISTAKABLY capture only if the tags or label matches. Preserve all original characters and spacing; Do not perform any auto-correction or modification of the extracted value. Other TAGS like 'Registry Number', 'slip no', 'Order No', or 'Document Number' or  column without any header should be IGNORED and SHOULD NOT be CAPTURED. UNMISTABLY, Ignore extraction If the headers 'Item Code' or 'Item ID' are not found, do not return any value as the item code."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "dataSource": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Keep the field value as 'OCR'.", "enum": ["OCR"]},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "lineTypeSectionTotalItem": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Return as 'ITEM' if the row is ITEM. Return as 'SECTION TOTAL' if the row is section total or Total. Return an empty string if not applicable or unknown.", "enum": ["ITEM", "SECTION TOTAL", ""]},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "sectionHeaderLineSectionType": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "For each line item, extract the DEPT code, DEFT code, Income center, Department, and medical department type (e.g., Laboratory, EYE Center, etc.). Prioritize extraction from the line item itself, and use the header section as a fallback source if these values are missing, as these codes and department types typically indicate the item's section or grouping. Ensure that the text extraction remains continuous and does not terminate upon encountering a special character within a word. You must also return the complete section header relevant to the line item; if the required data and the relevant header cannot be found, return an empty string."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "billsParticularsCostCenters": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract the 'Item Description' or 'Description' or 'Items'. Return an empty string if not found."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "qty": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract the 'QTY' or 'Quantity'. Return an empty string if not found."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "price": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract the 'price'. Return an empty string if not found."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "discount": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract the 'discount'. If it is '0.00' return '0.00' only. Return an empty string if not found (unless it's '0.00')."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "discountPercent": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract the 'discount percent'. Return an empty string if not found."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "paidByPatientHospitalBill": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract the 'paidByPatientHospitalBill'. Return an empty string if not found."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "philhealthHospBillPortionAmount": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract the 'philhealthHospBillPortionAmount'. Return an empty string if not found."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        },
                        "billsParticularsCostCenterAmount": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string", "description": "Extract the 'Gross Amount' or 'Gross AMT' or 'Total Amount' or 'Amount' or 'Hospital'. Return an empty string if not found."},
                                "labelBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for label [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if label not visible."
                                },
                                "valueBbox": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "Normalized bounding box for value [y_min, x_min, y_max, x_max] scaled 0-1000. Empty [0,0,0,0] if value not found."
                                }
                            }
                        }
                    },
                    "required": [
                        "claimId",
                        "lineId",
                        "serviceDateTime",
                        "itemCode",
                        "dataSource",
                        "lineTypeSectionTotalItem",
                        "sectionHeaderLineSectionType",
                        "billsParticularsCostCenters",
                        "qty",
                        "price",
                        "discount",
                        "discountPercent",
                        "paidByPatientHospitalBill",
                        "philhealthHospBillPortionAmount",
                        "billsParticularsCostCenterAmount"
                    ]
                }
            }
        }
    },
    thinking_config=types.ThinkingConfig(
      thinking_budget=-1,
    ),
  )

  result_text = ""
  for chunk in client.models.generate_content_stream(
    model = model,
    contents = contents,
    config = generate_content_config,
    ):
    result_text += chunk.text
  
  return result_text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            result_json = generate(filepath)
            # Clean up the uploaded file
            os.remove(filepath)
            
            # Parse the JSON to validate it
            result_data = json.loads(result_json)
            return jsonify(result_data)
        except Exception as e:
            # Clean up the uploaded file in case of error
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Invalid file type. Only PDF files are allowed.'}), 400

if __name__ == "__main__":
    # Check if running as web server or CLI
    import sys
    if len(sys.argv) > 1:
        # CLI mode
        parser = argparse.ArgumentParser(description="Process an image or PDF file with Gemini.")
        parser.add_argument("file_path", help="The path to the image or PDF file.")
        args = parser.parse_args()
        result = generate(args.file_path)
        print(result)
    else:
        # Web server mode
        app.run(host='0.0.0.0', port=8000, debug=True)
