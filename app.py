# app.py

import gradio as gr
import requests
import json

# --- Configuration ---
# MAIN INSIGHTS ENDPOINT (for summary, decisions, actions, sentiment)
MODAL_INSIGHTS_ENDPOINT_URL = "https://mehdinathani--ai-meeting-insights-service-v2-get-insights.modal.run"
# Q&A ENDPOINT (will likely be the main URL + /qna or similar - CHECK MODAL DEPLOYMENT OUTPUT)
MODAL_QNA_ENDPOINT_URL = "https://mehdinathani--ai-meeting-qna-service-v2-1-guardrails-ask-74022e.modal.run"


# --- Example Transcript (keep as is) ---
EXAMPLE_TRANSCRIPT = """Meeting Transcript
Date: June 5, 2025
Time: 10:00 AM - 11:00 AM
Location: Virtual (Zoom)
Participants: Alex Johnson (AJ), Maria Chen (MC), Raj Patel (RP), Sarah Lee (SL)

---

[10:00 AM] AJ: Good morning, everyone! Thanks for joining today’s project update meeting. Let’s get started with a quick round of updates. Maria, can you kick us off?

[10:02 AM] MC: Sure, Alex. The development team has completed the initial wireframes for the new app interface. We’re ready to share them for feedback by end of week. We’re also on track with the backend API integration, about 60% done.

[10:05 AM] RP: That’s great, Maria. On the marketing side, we’ve finalized the campaign strategy for Q3. We’re focusing on social media ads and have a draft budget ready. Sarah, how’s the content creation going?

[10:08 AM] SL: Content’s coming along well. We’ve got blog posts and video scripts drafted for the launch. I’ll need input from Maria’s team on technical details to ensure accuracy. Can we set up a sync later this week?

[10:10 AM] MC: Absolutely, let’s do Thursday afternoon. I’ll send a calendar invite.

[10:12 AM] AJ: Sounds good. Any roadblocks or resource needs anyone wants to flag?

[10:14 AM] RP: We might need additional budget for influencer partnerships. I’ll put together a proposal and share it by tomorrow.

[10:16 AM] SL: No major issues here, but I’d appreciate a quicker turnaround on design assets from the creative team.

[10:18 AM] AJ: Noted, Raj and Sarah. I’ll follow up with the creative team and review the budget proposal. Let’s move to next steps. Maria, what’s the timeline for the wireframe feedback?

[10:20 AM] MC: We’d like feedback by next Monday to stay on schedule. I’ll circulate the wireframes tomorrow morning.

[10:22 AM] AJ: Perfect. Raj, can you align the marketing timeline with that?

[10:23 AM] RP: Yep, we’ll sync our campaign prep to launch alongside the app release. I’ll confirm dates after Maria’s team finalizes the dev schedule.

[10:25 AM] SL: I’ll have the content team prioritize assets to match that timeline too.

[10:27 AM] AJ: Excellent. Anything else before we wrap up?

[10:28 AM] MC: Just a heads-up, we might need an extra developer for the final sprint. I’ll confirm after reviewing the workload.

[10:30 AM] AJ: Okay, keep me posted. Thanks, everyone, for the updates. Let’s reconvene next week, same time. I’ll send a summary of action items by EOD.

[10:32 AM] All: Sounds good, thanks!

[Meeting adjourned at 10:32 AM]

---

Action Items:
- Maria: Share wireframes by tomorrow, schedule sync with Sarah for Thursday.
- Raj: Submit influencer budget proposal by tomorrow.
- Sarah: Coordinate with creative team for faster design asset delivery.
- Alex: Follow up on creative team delays and review budget proposal.""" # Truncated for brevity

# --- Functions for Gradio ---
def clear_all_fields():
    return "", "", "", "", "", "", "" # transcript, summary, decisions, actions, sentiment, question, answer

def load_example():
    return EXAMPLE_TRANSCRIPT, "", "", "", "", "", "" # transcript, summary, decisions, actions, sentiment, question, answer

def get_all_insights_from_modal(transcript_text):
    # ... (This function remains mostly the same, just ensure MODAL_INSIGHTS_ENDPOINT_URL is used) ...
    # ... (and it returns 4 values for the 4 insight types) ...
    err_summary = "Error: Could not retrieve summary."
    err_decisions = "Error: Could not retrieve decisions."
    err_actions = "Error: Could not retrieve action items."
    err_sentiment = "Error: Could not retrieve sentiment."

    # Use the specific insights endpoint URL
    if MODAL_INSIGHTS_ENDPOINT_URL == "YOUR_MODAL_URL_FOR_ai-meeting-processor-v6-6-qna_MAIN_ENDPOINT" or \
       not MODAL_INSIGHTS_ENDPOINT_URL or \
       not MODAL_INSIGHTS_ENDPOINT_URL.startswith("https://"):
        error_msg = "Insights Modal endpoint URL not correctly configured in `app.py`."
        print(f"ERROR: {error_msg} Current value: {MODAL_INSIGHTS_ENDPOINT_URL}")
        return error_msg, err_decisions, err_actions, err_sentiment

    if not transcript_text.strip():
        return "Please enter some transcript text first.", "", "", "", "" # Added one empty string for sentiment
    
    # (The rest of this function is the same as your working v6.5, ensuring it returns 4 values)
    print(f"INFO: Sending transcript to Modal (Insights): {MODAL_INSIGHTS_ENDPOINT_URL}")
    headers = {"Content-Type": "application/json"}
    payload = {"transcript": transcript_text}
    try:
        response = requests.post(MODAL_INSIGHTS_ENDPOINT_URL, headers=headers, json=payload, timeout=300)
        print(f"INFO: Response from Modal (Insights). Status: {response.status_code}")
        print(f"DEBUG: Raw response text (Insights): >>>\n{response.text}\n<<<")
        response.raise_for_status()
        results = response.json()
        if results is None: raise json.JSONDecodeError("JSON parsed to None", response.text, 0)
        if "error" in results and results["error"]:
            return f"AI Service Error (Insights): {results['error']}", "", "", ""
        summary = results.get("summary", "Summary not provided.")
        decisions = results.get("decisions", "Decisions not provided.")
        actions = results.get("actions", "Action items not provided.")
        sentiment = results.get("sentiment", "Sentiment not provided.")
        return summary, decisions, actions, sentiment
    except Exception as e: # Simplified error return for brevity
        print(f"ERROR in get_all_insights_from_modal: {e}")
        return f"Error processing insights: {e}", err_decisions, err_actions, err_sentiment

# --- NEW Function to Call Modal Q&A Endpoint ---
def ask_question_on_transcript(transcript_text, question_text):
    """Calls the Modal Q&A endpoint."""
    err_answer = "Error: Could not retrieve answer."

    if MODAL_QNA_ENDPOINT_URL == "YOUR_MODAL_URL_FOR_ai-meeting-processor-v6-6-qna_QNA_ENDPOINT" or \
       not MODAL_QNA_ENDPOINT_URL or \
       not MODAL_QNA_ENDPOINT_URL.startswith("https://"):
        error_msg = "Q&A Modal endpoint URL not correctly configured in `app.py`."
        print(f"ERROR: {error_msg} Current value: {MODAL_QNA_ENDPOINT_URL}")
        return error_msg

    if not transcript_text.strip():
        return "Please provide the meeting transcript before asking a question."
    if not question_text.strip():
        return "Please enter a question to ask."

    print(f"INFO: Sending transcript and question to Modal (Q&A): {MODAL_QNA_ENDPOINT_URL}")
    headers = {"Content-Type": "application/json"}
    payload = {"transcript": transcript_text, "question": question_text}

    try:
        response = requests.post(MODAL_QNA_ENDPOINT_URL, headers=headers, json=payload, timeout=180) # Shorter timeout for Q&A
        print(f"INFO: Response from Modal (Q&A). Status: {response.status_code}")
        print(f"DEBUG: Raw response text (Q&A): >>>\n{response.text}\n<<<")
        response.raise_for_status()
        
        results = response.json()
        if results is None: raise json.JSONDecodeError("JSON parsed to None for Q&A", response.text, 0)

        if "error" in results and results["error"]:
            print(f"ERROR: Q&A Service (Modal) reported an error: {results['error']}")
            return f"Q&A Service Error: {results['error']}"
        
        answer = results.get("answer", "Answer not provided by AI service.")
        print("INFO: Successfully parsed Q&A answer.")
        return answer

    except Exception as e: # Simplified error return for brevity
        msg = f"Error during Q&A processing: {e}"
        print(f"ERROR: {msg}")
        return msg

# --- Gradio UI Definition ---
with gr.Blocks(title="AI Meeting Assistant Pro", theme=gr.themes.Soft()) as app_ui:
    gr.Markdown("# 🚀 AI Meeting Assistant Pro (with Q&A!) 🚀")
    gr.Markdown("Extract insights and ask questions about your meeting transcript.")

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
            decisions_output = gr.Markdown(label="Key Decisions Made")
        with gr.TabItem("Action Items (Markdown)"):
            action_items_output = gr.Markdown(label="Action Items Identified")
        with gr.TabItem("Sentiment Analysis"):
            sentiment_output = gr.Textbox(label="Overall Meeting Sentiment", interactive=False, lines=5)

    gr.Markdown("---")
    gr.Markdown("## ❓ Ask a Follow-up Question:")
    question_input = gr.Textbox(label="Your Question About the Transcript", placeholder="e.g., What did Bob say about the MFA library?")
    ask_qna_button = gr.Button("💬 Ask Question", variant="secondary")
    qna_answer_output = gr.Textbox(label="Answer", interactive=False, lines=5) # Or gr.Markdown() if you want formatted answers

    # --- Connect UI Elements to Functions ---
    # List of insight outputs for clearing/loading examples
    insight_outputs = [summary_output, decisions_output, action_items_output, sentiment_output]
    # All outputs including Q&A for full clear
    all_output_fields = insight_outputs + [question_input, qna_answer_output]


    process_button.click(
        fn=get_all_insights_from_modal, inputs=[transcript_input], outputs=insight_outputs,
        api_name="get_insights_v2", show_progress="full"
    )
    
    ask_qna_button.click(
        fn=ask_question_on_transcript, inputs=[transcript_input, question_input], outputs=[qna_answer_output],
        api_name="ask_qna", show_progress="full"
    )
    
    clear_button.click(fn=clear_all_fields, inputs=None, outputs=[transcript_input] + all_output_fields)
    example_button.click(fn=load_example, inputs=None, outputs=[transcript_input] + all_output_fields)

    gr.Markdown("---")
    gr.Markdown("Powered by Gradio & Modal. For the Hugging Face Agents & MCP Hackathon.")

if __name__ == "__main__":
    app_ui.launch(debug=True, show_error=True)