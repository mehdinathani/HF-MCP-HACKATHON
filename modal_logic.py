# modal_logic.py

import modal
import os
import asyncio # Still useful for the type check in the endpoint
from transformers import pipeline as transformers_pipeline
from fastapi.responses import JSONResponse # For explicit JSON response

# --- Modal App Definition ---
# Let's give it a new version name based on v6.4
app = modal.App(name="ai-meeting-processor-v6-5-features") # << New App Name

# --- Image Definition (No changes from your v6.4) ---
llm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi[standard]",
        "transformers>=4.38.0",
        "torch>=2.0.0",
        "accelerate>=0.25.0",
        "bitsandbytes>=0.41.3",
        "sentencepiece"
    )
    .env({
        "TRANSFORMERS_CACHE": "/cache/huggingface_cache",
        "HF_HOME": "/cache/huggingface_cache",
    })
)

# --- LLM Processor Class ---
@app.cls(
    image=llm_image,
    secrets=[modal.Secret.from_name("my-huggingface-secret")],
    gpu="A10G",
    container_idle_timeout=300, # Modal 1.0 uses this
    timeout=600,
)
class LLMProcessor:
    def __init__(self):
        self.text_generator = None
        self.model_name = "mistralai/Mistral-7B-Instruct-v0.2"
        # Updated version marker for logs
        print(f"MODAL LLMProcessor __init__ (v6.5-features): Instance created. Target model: {self.model_name}")

    @modal.enter()
    async def load_model_and_tokenizer(self):
        # Updated version marker
        print(f"MODAL LLMProcessor @modal.enter (v6.5-features): STARTED! Attempting to load model: {self.model_name}")
        
        hf_token_value = os.environ.get("HF_TOKEN") 
        
        if hf_token_value:
            print(f"MODAL LLMProcessor @modal.enter (v6.5-features): Successfully found and using HF_TOKEN (length: {len(hf_token_value)}).")
        else:
            print("MODAL LLMProcessor @modal.enter (v6.5-features): CRITICAL WARNING - HF_TOKEN not found. Model download may fail.")

        try:
            self.text_generator = transformers_pipeline(
                "text-generation", model=self.model_name, device_map="auto",
                torch_dtype="auto", trust_remote_code=True, token=hf_token_value
            )
            if self.text_generator.tokenizer.pad_token_id is None:
                self.text_generator.tokenizer.pad_token_id = self.text_generator.tokenizer.eos_token_id
                print(f"MODAL LLMProcessor @modal.enter (v6.5-features): Set pad_token_id.")
            print(f"MODAL LLMProcessor @modal.enter (v6.5-features): Model '{self.model_name}' LOADED SUCCESSFULLY!")
        except Exception as e:
            self.text_generator = None
            print(f"MODAL LLMProcessor @modal.enter (v6.5-features): CRITICAL ERROR LOADING MODEL: {e}")
            raise RuntimeError(f"Failed to load LLM model ({self.model_name}): {e}")

    async def _generate_text_from_prompt(self, prompt: str, max_new_tokens: int) -> str:
        if not self.text_generator:
            # Updated version marker
            print(f"MODAL LLMProcessor _generate_text (v6.5-features): ERROR - LLM pipeline not initialized.")
            raise RuntimeError("LLM pipeline not initialized.")
        
        print(f"MODAL LLMProcessor _generate_text (v6.5-features): Prompt (start): {prompt[:100]}...")
        outputs = self.text_generator(
            prompt, max_new_tokens=max_new_tokens, do_sample=True, temperature=0.6,
            top_p=0.9, pad_token_id=self.text_generator.tokenizer.eos_token_id,
        )
        if outputs and isinstance(outputs, list) and "generated_text" in outputs[0]:
            full_response = outputs[0]["generated_text"]
            parts = full_response.split("[/INST]", 1)
            if len(parts) > 1:
                print(f"MODAL LLMProcessor _generate_text (v6.5-features): Extracted part successfully.")
                return parts[1].strip()
            print(f"MODAL LLMProcessor _generate_text (v6.5-features): WARNING - No '[/INST]' marker.")
            prompt_end_index = full_response.rfind(prompt)
            if prompt_end_index != -1:
                start_of_generation = prompt_end_index + len(prompt)
                if start_of_generation < len(full_response): return full_response[start_of_generation:].strip()
            return full_response
        raise ValueError(f"MODAL LLMProcessor _generate_text (v6.5-features): LLM output unexpected: {outputs}")

    @modal.method()
    async def process_transcript_insights(self, transcript: str) -> dict:
        # Updated version marker
        print(f"MODAL LLMProcessor process_transcript_insights (v6.5-features): Called for transcript (start): {transcript[:70]}...")
        if not self.text_generator:
            print("ERROR MODAL LLMProcessor (v6.5-features): Text generator not available!")
            return {"summary": "Error: AI Model not loaded.", "decisions": "", "actions": "", "sentiment": "", "error": "LLM not loaded."}

        # Initialize results dictionary with the new sentiment field
        results = {"summary": "", "decisions": "", "actions": "", "sentiment": "", "error": ""}
        task_errors = []

        # --- 1. Generate Summary (Keep your existing good summary prompt) ---
        summary_prompt_template = """<s>[INST] You are an expert meeting summarizer.
Given the following meeting transcript, provide a concise summary that highlights the main topics discussed and key outcomes.
Focus on clarity and brevity. The summary should be directly usable and informative.
Do not add any conversational fluff, introductory remarks like "Here is the summary:", or concluding remarks. Just provide the summary itself.
Transcript:
---
{transcript_text}
---
[/INST]"""
        try:
            full_summary_prompt = summary_prompt_template.format(transcript_text=transcript)
            results["summary"] = await self._generate_text_from_prompt(full_summary_prompt, max_new_tokens=350)
        except Exception as e:
            err_msg = f"Error generating summary: {type(e).__name__} - {e}"
            print(f"MODAL LLMProcessor (v6.5-features): {err_msg}")
            results["summary"] = "Error: Could not generate summary from AI."
            task_errors.append(f"Summary: {err_msg}")

        # --- 2. Generate Decisions (Prompt updated for Markdown) ---
        decisions_prompt_template = """<s>[INST] You are an expert meeting analyst.
From the following meeting transcript, identify and list all key decisions that were made.
Format the decisions as a markdown bullet list (e.g., using '-' or '*' for each item).
If no clear decisions were made, state "No specific decisions were identified."
Do not add any conversational fluff. Just provide the markdown list of decisions or the 'no decisions' statement.
Transcript:
---
{transcript_text}
---
[/INST]"""
        try:
            full_decisions_prompt = decisions_prompt_template.format(transcript_text=transcript)
            results["decisions"] = await self._generate_text_from_prompt(full_decisions_prompt, max_new_tokens=250)
        except Exception as e:
            err_msg = f"Error generating decisions: {type(e).__name__} - {e}"
            print(f"MODAL LLMProcessor (v6.5-features): {err_msg}")
            results["decisions"] = "Error: Could not generate decisions from AI."
            task_errors.append(f"Decisions: {err_msg}")

        # --- 3. Generate Action Items (Prompt updated for Markdown) ---
        actions_prompt_template = """<s>[INST] You are an expert meeting analyst.
From the following meeting transcript, extract all action items. For each action item, if possible, identify who is responsible or needs to take action.
Format the action items as a markdown bullet list (e.g., using '-' or '*' for each item). Example format: "- [Action Item] (Assigned to: [Person/Team, if mentioned, otherwise N/A])".
If no action items are found, state "No specific action items were identified."
Do not add any conversational fluff.
Transcript:
---
{transcript_text}
---
[/INST]"""
        try:
            full_actions_prompt = actions_prompt_template.format(transcript_text=transcript)
            results["actions"] = await self._generate_text_from_prompt(full_actions_prompt, max_new_tokens=300)
        except Exception as e:
            err_msg = f"Error generating action items: {type(e).__name__} - {e}"
            print(f"MODAL LLMProcessor (v6.5-features): {err_msg}")
            results["actions"] = "Error: Could not generate action items from AI."
            task_errors.append(f"Actions: {err_msg}")

        # --- 4. Generate Sentiment Analysis (New Feature) ---
        sentiment_prompt_template = """<s>[INST]Analyze the overall sentiment of the following meeting transcript.
First, state the overall sentiment in one word: Positive, Negative, or Neutral.
Then, on a new line, provide a brief 1-2 sentence justification for your sentiment analysis.
Transcript:
---
{transcript_text}
---
[/INST]
""" # The LLM should follow with "Sentiment: [Word]\nJustification: [Text]" or similar
        try:
            full_sentiment_prompt = sentiment_prompt_template.format(transcript_text=transcript)
            results["sentiment"] = await self._generate_text_from_prompt(full_sentiment_prompt, max_new_tokens=100)
        except Exception as e:
            err_msg = f"Error generating sentiment: {type(e).__name__} - {e}"
            print(f"MODAL LLMProcessor (v6.5-features): {err_msg}")
            results["sentiment"] = "Error: Could not generate sentiment from AI."
            task_errors.append(f"Sentiment: {err_msg}")

        if task_errors: results["error"] = "; ".join(task_errors)
        print(f"MODAL LLMProcessor process_transcript_insights (v6.5-features): Processing complete. Returning results.")
        return results

# --- FastAPI Web Endpoint Definition (Using the v6.4 no-await logic that worked) ---
@app.function(
    image=llm_image,
    secrets=[modal.Secret.from_name("my-huggingface-secret")],
    timeout=180,
)
@modal.fastapi_endpoint(method="POST")
async def process_meeting_insights_endpoint(request_data: dict):
    transcript = request_data.get("transcript")
    if not transcript or not isinstance(transcript, str) or not transcript.strip():
        # Updated version marker
        print(f"MODAL ENDPOINT (v6.5-features): Invalid request. Data: {request_data}")
        return JSONResponse(content={"error": "Invalid request"}, status_code=400)

    # Updated version marker
    print(f"MODAL ENDPOINT (v6.5-features): Received transcript. Calling remote method.")
    insights = None
    try:
        processor = LLMProcessor()
        remote_call_result = processor.process_transcript_insights.remote(transcript=transcript)
        # Updated version marker
        print(f"MODAL ENDPOINT (v6.5-features): Type of remote_call_result: {type(remote_call_result)}")

        if asyncio.iscoroutine(remote_call_result) or asyncio.isfuture(remote_call_result) or hasattr(remote_call_result, '__await__'):
            # Updated version marker
            print(f"MODAL ENDPOINT (v6.5-features): remote_call_result IS awaitable. Awaiting.")
            insights = await remote_call_result
        elif isinstance(remote_call_result, dict):
            # Updated version marker
            print(f"MODAL ENDPOINT (v6.5-features): remote_call_result is ALREADY a dict.")
            insights = remote_call_result
        else:
            raise ValueError(f"Unexpected type from remote call: {type(remote_call_result)}")
        
        # Updated version marker
        print(f"MODAL ENDPOINT (v6.5-features): Insights received. Type: {type(insights)}")
        if isinstance(insights, dict):
            if "error" in insights and insights["error"]:
                 print(f"MODAL ENDPOINT (v6.5-features): Error from LLMProcessor: {insights['error']}")
            return JSONResponse(content=insights)
        else:
            return JSONResponse(content={"error": "Non-dict insights"}, status_code=500)
    except TypeError as te: # Should be less likely now
        print(f"CRITICAL TYPEERROR IN ENDPOINT (v6.5-features): {te}")
        return JSONResponse(content={"error": f"Endpoint TypeError: {te}"}, status_code=500)
    except Exception as e:
        print(f"CRITICAL ERROR MODAL ENDPOINT (v6.5-features): {type(e).__name__} - {e}")
        return JSONResponse(content={"error": f"Endpoint error: {e}"}, status_code=500)

# --- Local Entrypoint ---
@app.local_entrypoint()
async def main_local():
    # Updated version marker
    print("MODAL main_local (v6.5-features): Deploy with `modal deploy modal_logic.py`")
    print("App name: ai-meeting-processor-v6-5-features")