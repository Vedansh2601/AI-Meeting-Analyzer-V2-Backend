import azure.functions as func
import json
import logging
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

app = func.FunctionApp()

PROJECT_ENDPOINT = "https://hiremind-ai-dev-resource.services.ai.azure.com/api/projects/hiremind-ai-dev"
AGENT_NAME = "ai-notes-analyzer"


@app.route(route="AnalyzeMeetingV2", auth_level=func.AuthLevel.ANONYMOUS)
def AnalyzeMeetingV2(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('AnalyzeMeetingV2 function triggered.')

    # CORS: allow the React frontend (running on a different origin) to call this
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }

    if req.method == "OPTIONS":
        return func.HttpResponse(status_code=200, headers=headers)

    try:
        req_body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Request body must be valid JSON."}),
            status_code=400,
            headers=headers
        )

    notes = req_body.get("notes")
    if not notes or not notes.strip():
        return func.HttpResponse(
            json.dumps({"error": "Please provide a 'notes' field."}),
            status_code=400,
            headers=headers
        )

    try:
        credential = DefaultAzureCredential()
        project_client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=credential,
            allow_preview=True,
        )

        openai_client = project_client.get_openai_client(agent_name=AGENT_NAME)
        response = openai_client.responses.create(input=notes)

        raw_output = response.output_text
        logging.info(f"Raw agent output: {raw_output}")

        # The agent returns a JSON string - parse it so we return real JSON, not a JSON-encoded string
        analysis = json.loads(raw_output)

    except json.JSONDecodeError as e:
        logging.error(f"Agent did not return valid JSON: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "The agent returned an unexpected format."}),
            status_code=500,
            headers=headers
        )
    except Exception as e:
        logging.error(f"Error calling agent: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Something went wrong while analyzing the meeting notes."}),
            status_code=500,
            headers=headers
        )

    return func.HttpResponse(
        json.dumps(analysis),
        status_code=200,
        headers=headers
    )