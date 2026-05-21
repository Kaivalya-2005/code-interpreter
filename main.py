from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from io import StringIO
from dotenv import load_dotenv

import traceback
import sys
import os

from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini Client
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY")
)

# Request Model
class CodeRequest(BaseModel):
    code: str

# AI Response Model
class ErrorAnalysis(BaseModel):
    error_lines: List[int]

# Execute Python Code
def execute_python_code(code: str):

    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        exec(code)

        output = sys.stdout.getvalue()

        return {
            "success": True,
            "output": output
        }

    except Exception:

        output = traceback.format_exc()

        return {
            "success": False,
            "output": output
        }

    finally:
        sys.stdout = old_stdout

# AI Error Analysis
def analyze_error_with_ai(code: str, tb: str):

    prompt = f"""
Analyze this Python code and traceback.

Identify ONLY the exact line number(s)
where the error occurred.

CODE:
{code}

TRACEBACK:
{tb}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "error_lines": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.INTEGER
                        )
                    )
                },
                required=["error_lines"]
            )
        )
    )

    result = ErrorAnalysis.model_validate_json(
        response.text
    )

    return result.error_lines

# Main Endpoint
@app.post("/code-interpreter")
def code_interpreter(req: CodeRequest):

    execution = execute_python_code(req.code)

    # If code executed successfully
    if execution["success"]:

        return {
            "error": [],
            "result": execution["output"]
        }

    # If code has error
    try:
        error_lines = analyze_error_with_ai(
            req.code,
            execution["output"]
        )
    except Exception as e:
        return {
            "error": [],
            "result": str(e)
        }
    return {
        "error": error_lines,
        "result": execution["output"]
    }

# Root Route
@app.get("/")
def root():
    return {
        "message": "Code Interpreter API Running"
    }
