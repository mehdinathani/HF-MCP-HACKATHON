# modal_insights_app.py

import modal
import os
import asyncio
from transformers import pipeline as transformers_pipeline
from fastapi.responses import JSONResponse

# --- Modal App Definition for Insights ---
app = modal.App(name="ai-meeting-insights-service-v2") # << RENAMED to app, new service name

# --- Image Definition ---
llm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi[standard]", "transformers>=4.38.0", "torch>=2.0.0",
        "accelerate>=0.25.0", "bitsandbytes>=0.41.3", "sentencepiece"
    )
    .env({
        "TRANSFORMERS_CACHE": "/cache/huggingface_cache",
        "HF_HOME": "/cache/huggingface_cache",
    })
)

# --- LLM Processor Class for Insights ---
@app.cls( # Use app decorator
    image=llm_image, secrets=[modal.Secret.from_name("my-huggingface-secret")],
    gpu="A10G", container_idle_timeout=300, timeout=600,
)
class InsightsLLMProcessor:
    def __init__(self):
        self.text_generator = None
        self.model_name = "mistralai/Mistral-7B-Instruct-v0.2"
        print(f"INSIGHTS_SVC LLMProcessor __init__ (v2): Target: {self.model_name}")

    @modal.enter()
    async def load_model_and_tokenizer(self):
        print(f"INSIGHTS_SVC LLMProcessor @modal.enter (v2): Loading: {self.model_name}")
        hf_token_value = os.environ.get("HF_TOKEN")
        if not hf_token_value: print("INSIGHTS_SVC LLMProcessor @modal.enter (v2): WARNING - HF_TOKEN not found.")
        else: print(f"INSIGHTS_SVC LLMProcessor @modal.enter (v2): Using HF_TOKEN.")
        try:
            self.text_generator = transformers_pipeline(
                "text-generation", model=self.model_name, device_map="auto",
                torch_dtype="auto", trust_remote_code=True, token=hf_token_value
            )
            if self.text_generator.tokenizer.pad_token_id is None:
                self.text_generator.tokenizer.pad_token_id = self.text_generator.tokenizer.eos_token_id
                print(f"INSIGHTS_SVC LLMProcessor @modal.enter (v2): Set pad_token_id.")
            print(f"INSIGHTS_SVC LLMProcessor @modal.enter (v2): Model '{self.model_name}' LOADED.")
        except Exception as e:
            self.text_generator = None; print(f"INSIGHTS_SVC LLMProcessor @modal.enter (v2): ERROR LOADING MODEL: {e}")
            raise RuntimeError(f"Failed to load LLM model ({self.model_name}): {e}")

    async def _generate_text_from_prompt(self, prompt: str, max_new_tokens: int) -> str:
        if not self.text_generator: raise RuntimeError("LLM pipeline not initialized.")
        print(f"INSIGHTS_SVC _generate_text (v2): Prompt (start): {prompt[:70]}...")
        outputs = self.text_generator(
            prompt, max_new_tokens=max_new_tokens, do_sample=True, temperature=0.6,
            top_p=0.9, pad_token_id=self.text_generator.tokenizer.eos_token_id,
        )
        if outputs and isinstance(outputs, list) and "generated_text" in outputs[0]:
            full_response = outputs[0]["generated_text"]
            parts = full_response.split("[/INST]", 1)
            if len(parts) > 1: return parts[1].strip()
            prompt_end_index = full_response.rfind(prompt) 
            if prompt_end_index != -1:
                start_of_generation = prompt_end_index + len(prompt)
                if start_of_generation < len(full_response): return full_response[start_of_generation:].strip()
            return full_response
        raise ValueError(f"INSIGHTS_SVC _generate_text (v2): LLM output unexpected: {outputs}")

    @modal.method()
    async def process_transcript_insights(self, transcript: str) -> dict:
        print(f"INSIGHTS_SVC process_insights (v2): Transcript (start): {transcript[:70]}...")
        if not self.text_generator: return {"error": "LLM not loaded."}
        results = {"summary": "", "decisions": "", "actions": "", "sentiment": "", "error": ""}
        errors = []
        
        prompt_summary = f"<s>[INST] You are an expert meeting summarizer. Given the following meeting transcript, provide a concise summary that highlights the main topics discussed and key outcomes. Focus on clarity and brevity. The summary should be directly usable and informative. Do not add any conversational fluff, introductory remarks like \"Here is the summary:\", or concluding remarks. Just provide the summary itself.\nTranscript:\n---\n{transcript}\n---\n[/INST]\n"
        try: results["summary"] = await self._generate_text_from_prompt(prompt_summary, 350)
        except Exception as e: errors.append(f"Summary: {e}"); results["summary"] = "Error generating summary."
        
        prompt_decisions = f"<s>[INST] You are an expert meeting analyst. From the following meeting transcript, identify and list all key decisions that were made. Format the decisions as a markdown bullet list (e.g., using '-' or '*' for each item). If no clear decisions were made, state \"No specific decisions were identified.\" Do not add any conversational fluff. Just provide the markdown list of decisions or the 'no decisions' statement.\nTranscript:\n---\n{transcript}\n---\n[/INST]\n"
        try: results["decisions"] = await self._generate_text_from_prompt(prompt_decisions, 250)
        except Exception as e: errors.append(f"Decisions: {e}"); results["decisions"] = "Error generating decisions."
        
        prompt_actions = f"<s>[INST] You are an expert meeting analyst. From the following meeting transcript, extract all action items. For each action item, if possible, identify who is responsible or needs to take action. Format the action items as a markdown bullet list (e.g., using '-' or '*' for each item). Example format: \"- [Action Item] (Assigned to: [Person/Team, if mentioned, otherwise N/A])\". If no action items are found, state \"No specific action items were identified.\" Do not add any conversational fluff.\nTranscript:\n---\n{transcript}\n---\n[/INST]\n"
        try: results["actions"] = await self._generate_text_from_prompt(prompt_actions, 300)
        except Exception as e: errors.append(f"Actions: {e}"); results["actions"] = "Error generating actions."
        
        prompt_sentiment = f"<s>[INST]Analyze the overall sentiment of the following meeting transcript. First, state the overall sentiment in one word: Positive, Negative, or Neutral. Then, on a new line, provide a brief 1-2 sentence justification for your sentiment analysis.\nTranscript:\n---\n{transcript}\n---\n[/INST]\nSentiment and Justification:"
        try: results["sentiment"] = await self._generate_text_from_prompt(prompt_sentiment, 100)
        except Exception as e: errors.append(f"Sentiment: {e}"); results["sentiment"] = "Error analyzing sentiment."

        if errors: results["error"] = "; ".join(errors)
        print(f"INSIGHTS_SVC process_insights (v2): Processing complete.")
        return results

# --- FastAPI Web Endpoint for Insights ---
@app.function( # Use app decorator
    image=llm_image, secrets=[modal.Secret.from_name("my-huggingface-secret")], timeout=180
)
@modal.fastapi_endpoint(method="POST") # This will be at the root of this service's URL
async def get_insights(request_data: dict): 
    transcript = request_data.get("transcript")
    if not transcript or not isinstance(transcript, str) or not transcript.strip():
        print(f"INSIGHTS_SVC ENDPOINT (v2): Invalid transcript. Data: {request_data}")
        return JSONResponse(content={"error": "Invalid transcript"}, status_code=400)
    print(f"INSIGHTS_SVC ENDPOINT (v2): Received transcript. Calling remote method.")
    try:
        processor = InsightsLLMProcessor()
        remote_call_result = processor.process_transcript_insights.remote(transcript=transcript)
        
        insights = None
        print(f"INSIGHTS_SVC ENDPOINT (v2): Type of remote_call_result: {type(remote_call_result)}")
        if asyncio.iscoroutine(remote_call_result) or asyncio.isfuture(remote_call_result) or hasattr(remote_call_result, '__await__'):
            print(f"INSIGHTS_SVC ENDPOINT (v2): remote_call_result IS awaitable. Awaiting.")
            insights = await remote_call_result
        elif isinstance(remote_call_result, dict):
            print(f"INSIGHTS_SVC ENDPOINT (v2): remote_call_result is ALREADY a dict.")
            insights = remote_call_result
        else: 
            raise ValueError(f"Unexpected type from remote: {type(remote_call_result)}")
        
        print(f"INSIGHTS_SVC ENDPOINT (v2): Insights received. Type: {type(insights)}")
        if isinstance(insights, dict): return JSONResponse(content=insights)
        else: return JSONResponse(content={"error": "Non-dict insights"}, status_code=500)
    except Exception as e:
        print(f"INSIGHTS_SVC ENDPOINT (v2) ERROR: {type(e).__name__} - {e}")
        return JSONResponse(content={"error": f"Endpoint error: {str(e)}"}, status_code=500)

@app.local_entrypoint() # Use app decorator
async def main_insights():
    print("Deploy Insights Service: `modal deploy modal_insights_app.py`")
    print("App Name for Modal Service: ai-meeting-insights-service-v2")