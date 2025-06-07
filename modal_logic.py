# modal_logic.py

import modal
import os
import asyncio # Still useful for the type check
from transformers import pipeline as transformers_pipeline
from fastapi.responses import JSONResponse # For explicit JSON response

# --- Modal App Definition ---
app = modal.App(name="ai-meeting-processor-v6-4-no-await") # << Updated App Name

# --- Image Definition ---
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

# --- LLM Processor Class (No changes from v6.2/v6.3 here) ---
@app.cls(
    image=llm_image,
    secrets=[modal.Secret.from_name("my-huggingface-secret")],
    gpu="A10G",
    container_idle_timeout=300,
    timeout=600,
)
class LLMProcessor:
    def __init__(self):
        self.text_generator = None
        self.model_name = "mistralai/Mistral-7B-Instruct-v0.2"
        # Version marker consistent with the endpoint for log correlation
        print(f"MODAL LLMProcessor __init__ (v6.4-no-await): Instance created. Text generator is None. Target model: {self.model_name}")

    @modal.enter()
    async def load_model_and_tokenizer(self):
        print(f"MODAL LLMProcessor @modal.enter (v6.4-no-await): STARTED! Attempting to load model: {self.model_name}")
        
        hf_token_value = os.environ.get("HF_TOKEN") 
        
        if hf_token_value:
            print(f"MODAL LLMProcessor @modal.enter (v6.4-no-await): Successfully found and using HF_TOKEN (length: {len(hf_token_value)}).")
        else:
            print("MODAL LLMProcessor @modal.enter (v6.4-no-await): CRITICAL WARNING - HF_TOKEN not found in environment. Model download may fail.")

        try:
            self.text_generator = transformers_pipeline(
                "text-generation",
                model=self.model_name,
                device_map="auto",
                torch_dtype="auto",
                trust_remote_code=True,
                token=hf_token_value
            )
            if self.text_generator.tokenizer.pad_token_id is None:
                self.text_generator.tokenizer.pad_token_id = self.text_generator.tokenizer.eos_token_id
                print(f"MODAL LLMProcessor @modal.enter (v6.4-no-await): Set pad_token_id to eos_token_id.")

            print(f"MODAL LLMProcessor @modal.enter (v6.4-no-await): Model '{self.model_name}' LOADED SUCCESSFULLY!")
        except Exception as e:
            self.text_generator = None
            print(f"MODAL LLMProcessor @modal.enter (v6.4-no-await): CRITICAL ERROR LOADING MODEL: {type(e).__name__} - {e}")
            raise RuntimeError(f"Failed to load LLM model ({self.model_name}): {e}")


    async def _generate_text_from_prompt(self, prompt: str, max_new_tokens: int) -> str:
        if not self.text_generator:
            print(f"MODAL LLMProcessor _generate_text (v6.4-no-await): ERROR - LLM text_generator pipeline not initialized.")
            raise RuntimeError("LLM text_generator pipeline not initialized.")
        
        print(f"MODAL LLMProcessor _generate_text (v6.4-no-await): Generating with prompt (first 100 chars): {prompt[:100]}...")
        
        generated_outputs = self.text_generator(
            prompt,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
            pad_token_id=self.text_generator.tokenizer.eos_token_id,
        )
        
        if generated_outputs and isinstance(generated_outputs, list) and "generated_text" in generated_outputs[0]:
            full_llm_response = generated_outputs[0]["generated_text"]
            parts = full_llm_response.split("[/INST]", 1)
            if len(parts) > 1:
                generated_part = parts[1].strip()
                print(f"MODAL LLMProcessor _generate_text (v6.4-no-await): Successfully extracted generated part.")
                return generated_part
            else:
                print(f"MODAL LLMProcessor _generate_text (v6.4-no-await): WARNING - Could not find '[/INST]' marker in LLM response.")
                prompt_end_index = full_llm_response.rfind(prompt)
                if prompt_end_index != -1:
                    start_of_generation = prompt_end_index + len(prompt)
                    if start_of_generation < len(full_llm_response):
                        return full_llm_response[start_of_generation:].strip()
                return full_llm_response
        else:
            print(f"MODAL LLMProcessor _generate_text (v6.4-no-await): ERROR - Unexpected output format from text_generator: {generated_outputs}")
            raise ValueError("LLM returned an unexpected output format.")


    @modal.method()
    async def process_transcript_insights(self, transcript: str) -> dict:
        print(f"MODAL LLMProcessor process_transcript_insights (v6.4-no-await): Method called for transcript (first 70): {transcript[:70]}...")

        if not self.text_generator:
            print("ERROR MODAL LLMProcessor (v6.4-no-await): Text generator not available!")
            return {
                "summary": "Error: AI Model component (text_generator) failed to load or was not available.",
                "decisions": "", "actions": "", "error": "LLM text_generator not initialized or unavailable."
            }

        results = {"summary": "", "decisions": "", "actions": "", "error": ""}
        task_errors = []

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
            print(f"MODAL LLMProcessor (v6.4-no-await): {err_msg}")
            results["summary"] = "Error: Could not generate summary from AI."
            task_errors.append(f"Summary: {err_msg}")

        decisions_prompt_template = """<s>[INST] You are an expert meeting analyst.
From the following meeting transcript, identify and list all key decisions that were made.
If multiple decisions were made, list each one clearly, perhaps as bullet points.
If no clear decisions were made, state "No specific decisions were identified."
Do not add any conversational fluff. Just provide the decisions or the 'no decisions' statement.
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
            print(f"MODAL LLMProcessor (v6.4-no-await): {err_msg}")
            results["decisions"] = "Error: Could not generate decisions from AI."
            task_errors.append(f"Decisions: {err_msg}")

        actions_prompt_template = """<s>[INST] You are an expert meeting analyst.
From the following meeting transcript, extract all action items. For each action item, if possible, identify who is responsible or needs to take action.
List the action items clearly, for example, as bullet points in the format: "- [Action Item] (Assigned to: [Person/Team, if mentioned, otherwise N/A])".
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
            print(f"MODAL LLMProcessor (v6.4-no-await): {err_msg}")
            results["actions"] = "Error: Could not generate action items from AI."
            task_errors.append(f"Actions: {err_msg}")

        if task_errors:
            results["error"] = "; ".join(task_errors)
        
        print(f"MODAL LLMProcessor process_transcript_insights (v6.4-no-await): Processing complete. Returning results.")
        return results

# --- FastAPI Web Endpoint Definition (THIS IS THE MODIFIED PART for v6.4) ---
@app.function(
    image=llm_image,
    secrets=[modal.Secret.from_name("my-huggingface-secret")],
    timeout=180,
)
@modal.fastapi_endpoint(method="POST")
async def process_meeting_insights_endpoint(request_data: dict): # Function remains async
    transcript = request_data.get("transcript")
    
    if not transcript or not isinstance(transcript, str) or not transcript.strip():
        print(f"MODAL ENDPOINT (v6.4-no-await): Invalid request - 'transcript' missing, not a string, or empty. Data: {request_data}")
        return JSONResponse(content={"summary": "", "decisions": "", "actions": "", "error": "Invalid request: 'transcript' field missing, not a string, or empty."}, status_code=400)

    print(f"MODAL ENDPOINT (v6.4-no-await): Received transcript (first 70 chars): '{transcript[:70]}...'. Calling LLMProcessor().process_transcript_insights.remote().")
    
    insights = None # Initialize insights

    try:
        processor = LLMProcessor()
        
        # Make the call and store whatever .remote() returns
        remote_call_result = processor.process_transcript_insights.remote(transcript=transcript)
        
        print(f"MODAL ENDPOINT (v6.4-no-await): Type of remote_call_result (from .remote()): {type(remote_call_result)}")

        # Check if the result from .remote() is awaitable or already a dict
        if asyncio.iscoroutine(remote_call_result) or asyncio.isfuture(remote_call_result) or hasattr(remote_call_result, '__await__'):
            print(f"MODAL ENDPOINT (v6.4-no-await): remote_call_result IS awaitable. Awaiting it now.")
            insights = await remote_call_result
        elif isinstance(remote_call_result, dict):
            print(f"MODAL ENDPOINT (v6.4-no-await): remote_call_result is ALREADY a dict. Using it directly.")
            insights = remote_call_result # It's already the dictionary!
        else:
            # This would be very strange if it's neither awaitable nor a dict
            err_msg = f"Internal error: .remote() call returned an unexpected type: {type(remote_call_result)}"
            print(f"MODAL ENDPOINT (v6.4-no-await): {err_msg}")
            return JSONResponse(content={"summary": "", "decisions": "", "actions": "", "error": err_msg}, status_code=500)

        print(f"MODAL ENDPOINT (v6.4-no-await): Type of insights (after potential await/direct assignment): {type(insights)}")
        print(f"MODAL ENDPOINT (v6.4-no-await): Insights content: {insights}") # Be careful if insights is very large

        if isinstance(insights, dict):
            # Check for an error key from the LLMProcessor itself if one was set
            if "error" in insights and insights["error"]: # Check if error key exists and is non-empty
                 print(f"MODAL ENDPOINT (v6.4-no-await): Error reported by LLMProcessor: {insights['error']}")
            # Always return JSONResponse for consistency from the endpoint
            return JSONResponse(content=insights) 
        else:
            # This case should ideally be caught by the type checks above
            err_msg = f"Internal error: AI service processing resulted in an unexpected data type: {type(insights)}"
            print(f"MODAL ENDPOINT (v6.4-no-await): {err_msg}")
            return JSONResponse(content={"summary": "", "decisions": "", "actions": "", "error": err_msg}, status_code=500)

    except TypeError as te: # This specific TypeError should now be less likely with the check
        print(f"CRITICAL TYPEERROR IN ENDPOINT (v6.4-no-await): {te}")
        # This log indicates that the type check itself might have an issue or an await was still somehow applied to a dict
        error_content = {
            "summary": "", "decisions": "", "actions": "",
            "error": f"Internal TypeError in AI processing: {str(te)}. This suggests an issue with async/await handling."
        }
        return JSONResponse(content=error_content, status_code=500)
    except Exception as e:
        print(f"CRITICAL ERROR MODAL ENDPOINT (v6.4-no-await): An unexpected exception occurred: {type(e).__name__} - {e}")
        error_content = {
            "summary": "", "decisions": "", "actions": "",
            "error": f"Critical unexpected error in AI endpoint: {type(e).__name__} - {str(e)}."
        }
        return JSONResponse(content=error_content, status_code=500)

# --- Local Entrypoint ---
@app.local_entrypoint()
async def main_local():
    print("MODAL main_local (v6.4-no-await): This entrypoint is primarily for `modal deploy`.")
    print("App name for deployment: ai-meeting-processor-v6-4-no-await")