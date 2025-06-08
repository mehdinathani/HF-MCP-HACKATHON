# app.py

import gradio as gr
import requests
import json

# --- Configuration ---
# !!! IMPORTANT: PASTE THE CORRECT MODAL DEPLOYMENT URL FOR "ai-meeting-processor-v6-5-features" HERE !!!
MODAL_ENDPOINT_URL = "https://mehdinathani--ai-meeting-processor-v6-5-features-process-069515.modal.run"

# --- Example Transcript ---
EXAMPLE_TRANSCRIPT = """Meeting Title: Project Alpha Sync
Date: 2025-06-10
Attendees: Alice, Bob, Charlie, Diana

Alice: Okay team, let's kick off. Bob, any updates on the user authentication module?
Bob: Yes, good progress. I've completed the backend logic and basic unit tests. I expect to have the API endpoints ready for integration by Wednesday. I did hit a snag with the new MFA library, it seems to have a conflict with our current logging setup. Will need some time to debug that, or find an alternative.
Alice: Okay, thanks Bob. Prioritize getting the core endpoints ready. We can tackle the MFA conflict as a separate issue if it becomes a blocker. Charlie, how are the UI mockups for the dashboard coming along?
Charlie: Almost there. I've incorporated the feedback from last week's review. I should have the final mockups ready for review by end of day tomorrow. Diana, could you schedule a 30-min review slot for Thursday morning?
Diana: Will do, Charlie. I'll send out an invite.
Alice: Great. And Diana, any updates on the Q3 marketing campaign proposal?
Diana: The draft is ready. Key focus areas are social media engagement and a partnership with 'TechExplained' YouTube channel. I need budget approval for the influencer collaboration, around $5,000.
Alice: Understood. Bob, please ensure your API docs are clear for Charlie. Charlie, focus on the main dashboard view. Diana, please send me the budget proposal by EOD today for review. Any other business? No? Okay, good meeting everyone.
"""

# --- Functions for Gradio ---
def clear_all_fields():
    """Clears all input and output fields."""
    return "", "", "", "", "" # transcript, summary, decisions, actions, sentiment

def load_example():
    """Loads the example transcript into the input field and clears outputs."""
    return EXAMPLE_TRANSCRIPT, "", "", "", ""

def get_all_insights_from_modal(transcript_text):
    """Calls the Modal endpoint and handles response."""
    err_summary = "Error: Could not retrieve summary."
    err_decisions = "Error: Could not retrieve decisions."
    err_actions = "Error: Could not retrieve action items."
    err_sentiment = "Error: Could not retrieve sentiment."

    if MODAL_ENDPOINT_URL == "YOUR_NEW_MODAL_ENDPOINT_URL_HERE_FOR_V6_5" or not MODAL_ENDPOINT_URL.startswith("https://"):
        error_msg = "Modal endpoint URL not correctly configured in `app.py`."
        print(f"ERROR: {error_msg} Current value: {MODAL_ENDPOINT_URL}")
        return error_msg, err_decisions, err_actions, err_sentiment

    if not transcript_text.strip():
        return "Please enter some transcript text first.", "", "", "", ""

    print(f"INFO: Sending transcript to Modal: {MODAL_ENDPOINT_URL}")
    headers = {"Content-Type": "application/json"}
    payload = {"transcript": transcript_text}

    try:
        response = requests.post(MODAL_ENDPOINT_URL, headers=headers, json=payload, timeout=300) # 5 min timeout
        print(f"INFO: Response from Modal. Status: {response.status_code}")
        print(f"DEBUG: Raw response text: >>>\n{response.text}\n<<<")
        response.raise_for_status()
        
        results = response.json()
        if results is None: # Should not happen if JSON is valid but empty object, but good check
            raise json.JSONDecodeError("JSON parsed to None", response.text, 0)

        if "error" in results and results["error"]: # Check for error key from Modal service itself
            print(f"ERROR: AI Service (Modal) reported an error: {results['error']}")
            # Display the service's error in the summary field, or a dedicated error display
            return f"AI Service Error: {results['error']}", "", "", ""

        summary = results.get("summary", "Summary not provided.")
        decisions = results.get("decisions", "Decisions not provided.")
        actions = results.get("actions", "Action items not provided.")
        sentiment = results.get("sentiment", "Sentiment not provided.")
        
        print("INFO: Successfully parsed insights.")
        return summary, decisions, actions, sentiment

    except requests.exceptions.Timeout:
        msg = "Request to AI service timed out. Please try again."
        print(f"ERROR: {msg}")
        return msg, err_decisions, err_actions, err_sentiment
    except requests.exceptions.HTTPError as http_err:
        msg = f"HTTP error: {http_err.response.status_code} {http_err.response.reason}. Check Modal logs."
        print(f"ERROR: {msg}\nRaw Response: {http_err.response.text}")
        return msg, err_decisions, err_actions, err_sentiment
    except (requests.exceptions.RequestException, json.JSONDecodeError) as req_err:
        msg = f"Network/JSON error: {req_err}. Check URL & Modal status."
        print(f"ERROR: {msg}")
        return msg, err_decisions, err_actions, err_sentiment
    except Exception as e:
        msg = f"Critical unexpected error in Gradio app: {e}"
        print(f"ERROR: {msg}")
        return msg, err_decisions, err_actions, err_sentiment

# --- Gradio UI Definition ---
with gr.Blocks(title="AI Meeting Assistant Enhanced", theme=gr.themes.Soft()) as app_ui:
    gr.Markdown("# 🚀 AI Meeting Assistant - Enhanced Insights 🚀")
    gr.Markdown("Paste your meeting transcript to extract summary, decisions, action items, and sentiment.")

    with gr.Row():
        transcript_input = gr.Textbox(
            lines=15, label="Paste Full Meeting Transcript Here",
            placeholder="Enter the complete meeting transcript..."
        )

    with gr.Row():
        process_button = gr.Button("✨ Get All Insights!", variant="primary")
        clear_button = gr.Button("Clear All")
        example_button = gr.Button("Load Example Transcript")
    
    gr.Markdown("---")
    gr.Markdown("## 💡 Insights Extracted:")

    with gr.Tabs():
        with gr.TabItem("Summary"):
            summary_output = gr.Textbox(label="Meeting Summary", interactive=False, lines=10)
        with gr.TabItem("Key Decisions (Markdown)"):
            # Changed to Markdown component
            decisions_output = gr.Markdown(label="Key Decisions Made")
        with gr.TabItem("Action Items (Markdown)"):
            # Changed to Markdown component
            action_items_output = gr.Markdown(label="Action Items Identified")
        with gr.TabItem("Sentiment Analysis"):
            sentiment_output = gr.Textbox(label="Overall Meeting Sentiment", interactive=False, lines=5) # Or gr.Markdown if sentiment output is formatted

    # --- Connect UI Elements to Functions ---
    process_button.click(
        fn=get_all_insights_from_modal,
        inputs=[transcript_input],
        outputs=[summary_output, decisions_output, action_items_output, sentiment_output],
        api_name="get_insights_v2",
        show_progress="full" # Adds a progress indicator during processing
    )

    # Temporary list for clearing/loading examples
    all_outputs = [summary_output, decisions_output, action_items_output, sentiment_output]
    
    clear_button.click(
        fn=clear_all_fields,
        inputs=None, # No direct inputs needed for clear
        outputs=[transcript_input] + all_outputs
    )
    
    example_button.click(
        fn=load_example,
        inputs=None, # No direct inputs needed for load example
        outputs=[transcript_input] + all_outputs
    )

    gr.Markdown("---")
    gr.Markdown("Powered by Gradio & Modal. For the Hugging Face Agents & MCP Hackathon.")

# --- Launch the Gradio App ---
if __name__ == "__main__":
    app_ui.launch(debug=True, show_error=True)