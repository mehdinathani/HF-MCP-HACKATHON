import gradio as gr
import requests  # For making HTTP requests
import json      # For parsing JSON and json.JSONDecodeError

# --- Configuration ---
# !!! IMPORTANT: PASTE THE CORRECT MODAL DEPLOYMENT URL HERE !!!
# This URL was provided when you ran `modal deploy modal_logic.py`
# Example: "https://yourusername--ai-meeting-processor-vX-your-function-name.modal.run"
MODAL_ENDPOINT_URL = "https://mehdinathani--ai-meeting-processor-v6-4-no-await-process-02ef21.modal.run" # <-- YOUR ACTUAL URL

# --- Function to Call the Modal LLM Service ---
def get_all_insights(transcript_text):
    """
    Calls the Modal endpoint to get the summary, decisions, and action items
    for the given meeting transcript.
    """
    # Default error messages for each output field
    err_summary = "Error: Could not retrieve summary."
    err_decisions = "Error: Could not retrieve decisions."
    err_actions = "Error: Could not retrieve action items."

    # Validate Modal endpoint configuration
    if "YOUR_MODAL_DEPLOYED_WEB_ENDPOINT_URL_HERE" in MODAL_ENDPOINT_URL or not MODAL_ENDPOINT_URL or "https://mehdinathani--ai-meeting-processor-v6-4-no-await-process-02ef21.modal.run" != MODAL_ENDPOINT_URL : # A bit of a self-check if placeholder is still there
        # This check should be updated if you copy this code for a new endpoint.
        # For now, it also serves as a reminder if the placeholder URL is accidentally used.
        # if MODAL_ENDPOINT_URL == "YOUR_MODAL_DEPLOYED_WEB_ENDPOINT_URL_HERE": # Simpler check
        print(f"ERROR: MODAL_ENDPOINT_URL is not correctly configured. Current value: {MODAL_ENDPOINT_URL}")
        return "Modal endpoint URL not correctly configured in `app.py`. Please verify.", err_decisions, err_actions

    # Validate transcript input
    if not transcript_text.strip():
        return "Please enter some transcript text first.", "", ""

    print(f"INFO: Sending transcript to Modal endpoint: {MODAL_ENDPOINT_URL}")
    print(f"INFO: Transcript (first 100 chars): {transcript_text[:100]}...")

    headers = {"Content-Type": "application/json"}
    # The payload key "transcript" must match what your Modal endpoint function expects.
    payload = {"transcript": transcript_text}

    try:
        # Make the POST request to the Modal endpoint
        # Increased timeout to accommodate model loading and processing on Modal.
        response = requests.post(MODAL_ENDPOINT_URL, headers=headers, json=payload, timeout=300) # 5 minutes timeout
        
        print(f"INFO: Response received from Modal. Status Code: {response.status_code}")
        
        # --- Crucial Debugging Step: Print raw response text ---
        print(f"DEBUG: Raw response text from Modal: >>>\n{response.text}\n<<<")
        # --- End Debugging Step ---

        # Raise an HTTPError for bad responses (4xx client errors or 5xx server errors)
        response.raise_for_status() 
        
        # Attempt to parse the response as JSON
        try:
            results = response.json() # Expecting a dictionary from Modal
        except json.JSONDecodeError as json_err:
            print(f"ERROR: Failed to decode JSON from Modal response. Error: {json_err}")
            print(f"DEBUG: The raw response (printed above) was not valid JSON.")
            return "Error: AI service returned an invalid response format (not JSON).", err_decisions, err_actions

        # Check if parsing JSON resulted in None (e.g., if Modal returned JSON 'null')
        if results is None:
            print("ERROR: response.json() parsed to None. Modal endpoint might have returned JSON 'null'.")
            return "Error: AI service returned no valid data structure.", err_decisions, err_actions
        
        # Check if the Modal endpoint itself reported an error within the JSON response
        if "error" in results and results["error"]:
            print(f"ERROR: AI Service (Modal) reported an error: {results['error']}")
            # Display the service's error in the summary field, or create a dedicated error display
            return f"AI Service Error: {results['error']}", "", ""

        # Extract the insights, providing default messages if keys are missing
        summary = results.get("summary", "Summary not provided by AI service.")
        decisions = results.get("decisions", "Decisions not provided by AI service.")
        actions = results.get("actions", "Action items not provided by AI service.")
        
        print("INFO: Successfully parsed insights from Modal.")
        return summary, decisions, actions

    except requests.exceptions.Timeout:
        print(f"ERROR: Request to Modal timed out after 300 seconds.")
        return "The request to the AI service timed out. It might be processing a very long transcript or experiencing high load. Please try again with a shorter text or later.", err_decisions, err_actions
    
    except requests.exceptions.HTTPError as http_err:
        # This block will be entered if response.raise_for_status() detects an HTTP error.
        # The raw response text (which might contain Modal's error details) was already printed.
        print(f"ERROR: HTTP error occurred: {http_err} - Status: {http_err.response.status_code}")
        return f"Error connecting to AI service (HTTP {http_err.response.status_code} {http_err.response.reason}). Check Modal logs for details (raw response printed above).", err_decisions, err_actions

    except requests.exceptions.RequestException as req_err:
        # For other network issues (DNS failure, connection refused, etc.)
        print(f"ERROR: Network request exception occurred: {req_err}")
        return f"Error connecting to AI service: {req_err}. Please check your network connection and the endpoint URL.", err_decisions, err_actions
    
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"ERROR: An unexpected error occurred in get_all_insights: {type(e).__name__} - {e}")
        return f"A critical unexpected error occurred in the Gradio app: {e}. Please check the application logs.", err_decisions, err_actions


# --- Gradio UI Definition ---
with gr.Blocks(title="AI Meeting Assistant", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🚀 AI Meeting Assistant 🚀")
    gr.Markdown("Paste your meeting transcript below to extract a summary, key decisions, and action items.")

    with gr.Row():
        transcript_input = gr.Textbox(
            lines=15,
            label="Paste Full Meeting Transcript Here",
            placeholder="Enter the complete meeting transcript..."
        )

    process_button = gr.Button("✨ Get Insights!", variant="primary")

    gr.Markdown("---") # Visual separator
    gr.Markdown("## 💡 Insights Extracted:")

    # Using Tabs to neatly organize the different types of insights
    with gr.Tabs():
        with gr.TabItem("Summary"):
            summary_output = gr.Textbox(
                label="Meeting Summary", 
                interactive=False, # Output field, not editable by user
                lines=10 
            )
        with gr.TabItem("Key Decisions"):
            decisions_output = gr.Textbox(
                label="Key Decisions Made", 
                interactive=False, 
                lines=7 
            )
        with gr.TabItem("Action Items"):
            action_items_output = gr.Textbox(
                label="Action Items Identified", 
                interactive=False, 
                lines=7 
            )

    # Connect the button click event to the 'get_all_insights' function
    process_button.click(
        fn=get_all_insights,
        inputs=[transcript_input], # The transcript_input Textbox is the input
        outputs=[summary_output, decisions_output, action_items_output], # Results go to these Textboxes
        api_name="get_insights" # Optional: allows calling this function via Gradio's API if hosted
    )

    gr.Markdown("---")
    gr.Markdown("Powered by Gradio & Modal. For the Hugging Face Agents & MCP Hackathon.")

# --- Launch the Gradio App ---
if __name__ == "__main__":
    # debug=True provides helpful debugging information in the console.
    # show_error=True displays Python errors directly in the browser during development.
    app.launch(debug=True, show_error=True)