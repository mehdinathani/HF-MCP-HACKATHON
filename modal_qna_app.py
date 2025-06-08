# modal_qna_app.py

import modal
import os
import asyncio
from transformers import pipeline as transformers_pipeline
from fastapi.responses import JSONResponse

# --- Modal App Definition for Q&A ---
# Adding a version to the app name for this change
app = modal.App(name="ai-meeting-qna-service-v2-1-guardrails") 

# --- Image Definition (can be the same as insights app) ---
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

# --- LLM Processor Class for Q&A ---
@app.cls( 
    image=llm_image, secrets=[modal.Secret.from_name("my-huggingface-secret")],
    gpu="A10G", container_idle_timeout=300, timeout=180,
)
class QnALLMProcessor:
    def __init__(self):
        self.text_generator = None
        self.model_name = "mistralai/Mistral-7B-Instruct-v0.2"
        # Updated version marker
        print(f"QNA_SVC LLMProcessor __init__ (v2.1-guardrails): Target: {self.model_name}")

    @modal.enter()
    async def load_model_and_tokenizer(self):
        # Updated version marker
        print(f"QNA_SVC LLMProcessor @modal.enter (v2.1-guardrails): Loading: {self.model_name}")
        hf_token_value = os.environ.get("HF_TOKEN")
        if not hf_token_value: print("QNA_SVC LLMProcessor @modal.enter (v2.1-guardrails): WARNING - HF_TOKEN not found.")
        else: print(f"QNA_SVC LLMProcessor @modal.enter (v2.1-guardrails): Using HF_TOKEN.")
        try:
            self.text_generator = transformers_pipeline(
                "text-generation", model=self.model_name, device_map="auto",
                torch_dtype="auto", trust_remote_code=True, token=hf_token_value
            )
            if self.text_generator.tokenizer.pad_token_id is None:
                self.text_generator.tokenizer.pad_token_id = self.text_generator.tokenizer.eos_token_id
                print(f"QNA_SVC LLMProcessor @modal.enter (v2.1-guardrails): Set pad_token_id.")
            print(f"QNA_SVC LLMProcessor @modal.enter (v2.1-guardrails): Model '{self.model_name}' LOADED.")
        except Exception as e:
            self.text_generator = None; print(f"QNA_SVC LLMProcessor @modal.enter (v2.1-guardrails): ERROR LOADING MODEL: {e}")
            raise RuntimeError(f"Failed to load LLM model ({self.model_name}): {e}")

    async def _generate_text_from_prompt(self, prompt: str, max_new_tokens: int) -> str:
        if not self.text_generator: raise RuntimeError("LLM pipeline not initialized.")
        # Updated version marker
        print(f"QNA_SVC _generate_text (v2.1-guardrails): Prompt (start): {prompt[:70]}...")
        outputs = self.text_generator(
            prompt, max_new_tokens=max_new_tokens, do_sample=True, temperature=0.4, # Slightly lower temp for more focused Q&A
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
        raise ValueError(f"QNA_SVC _generate_text (v2.1-guardrails): LLM output unexpected: {outputs}")

    @modal.method()
    async def answer_question_on_transcript(self, transcript: str, question: str) -> dict:
        # Updated version marker
        print(f"QNA_SVC answer_question (v2.1-guardrails): Q: '{question}' on transcript (start): {transcript[:70]}...")
        if not self.text_generator:
            return {"answer": "Error: AI Model not loaded.", "error": "LLM not loaded."}

        # --- MODIFIED PROMPT FOR GUARDRAILS ---
        qna_prompt_template = """<s>[INST]You are an AI assistant specialized in answering questions based ONLY on the provided meeting transcript.
Your primary goal is to determine if the user's question can be answered using the information within the transcript.

Carefully review the meeting transcript below. Then, analyze the user's question.

1. If the question is directly and clearly answerable from the transcript, provide a concise answer based SOLELY on the transcript.
2. If the question is about a topic NOT discussed or mentioned in the transcript, you MUST respond with one of the following phrases:
   - "I'm sorry, but that topic does not seem to be covered in this meeting transcript."
   - "The provided transcript does not contain information about that."
   - "Based on the transcript, there is no discussion related to your question about [briefly mention question topic, e.g., 'the weather']."
   Do NOT attempt to answer questions for which the transcript provides no information. Do not use external knowledge.

Meeting Transcript:
---
{transcript_text}
---

User's Question: {user_question}
[/INST]
Answer:"""
        try:
            full_qna_prompt = qna_prompt_template.format(transcript_text=transcript, user_question=question)
            answer = await self._generate_text_from_prompt(full_qna_prompt, max_new_tokens=200)
            # Updated version marker
            print(f"QNA_SVC answer_question (v2.1-guardrails): Answer generated.")
            return {"answer": answer, "error": ""}
        except Exception as e:
            err_msg = f"Error generating answer: {type(e).__name__} - {e}"
            # Updated version marker
            print(f"QNA_SVC answer_question (v2.1-guardrails): {err_msg}")
            return {"answer": "Error: Could not generate answer from AI.", "error": err_msg}

# --- FastAPI Web Endpoint for Q&A (No changes to the endpoint logic itself) ---
@app.function(
    image=llm_image, secrets=[modal.Secret.from_name("my-huggingface-secret")], timeout=120
)
@modal.fastapi_endpoint(method="POST")
async def ask_question(request_data: dict): 
    transcript = request_data.get("transcript")
    question = request_data.get("question")
    if not transcript or not isinstance(transcript, str) or not transcript.strip() or \
       not question or not isinstance(question, str) or not question.strip():
        # Updated version marker
        print(f"QNA_SVC ENDPOINT (v2.1-guardrails): Invalid transcript/question. Data: {request_data}")
        return JSONResponse(content={"error": "Invalid transcript/question"}, status_code=400)
    # Updated version marker
    print(f"QNA_SVC ENDPOINT (v2.1-guardrails): Received Q: '{question}'. Calling remote method.")
    try:
        processor = QnALLMProcessor()
        remote_call_result = processor.answer_question_on_transcript.remote(transcript=transcript, question=question)
        
        answer_response = None
        # Updated version marker
        print(f"QNA_SVC ENDPOINT (v2.1-guardrails): Type of remote_call_result: {type(remote_call_result)}")
        if asyncio.iscoroutine(remote_call_result) or asyncio.isfuture(remote_call_result) or hasattr(remote_call_result, '__await__'):
            # Updated version marker
            print(f"QNA_SVC ENDPOINT (v2.1-guardrails): remote_call_result IS awaitable. Awaiting.")
            answer_response = await remote_call_result
        elif isinstance(remote_call_result, dict):
            # Updated version marker
            print(f"QNA_SVC ENDPOINT (v2.1-guardrails): remote_call_result is ALREADY a dict.")
            answer_response = remote_call_result
        else: 
            raise ValueError(f"Unexpected type from remote: {type(remote_call_result)}")
        
        # Updated version marker
        print(f"QNA_SVC ENDPOINT (v2.1-guardrails): Q&A response received. Type: {type(answer_response)}")
        if isinstance(answer_response, dict): return JSONResponse(content=answer_response)
        else: return JSONResponse(content={"error": "Non-dict Q&A response"}, status_code=500)
    except Exception as e:
        # Updated version marker
        print(f"QNA_SVC ENDPOINT (v2.1-guardrails) ERROR: {type(e).__name__} - {e}")
        return JSONResponse(content={"error": f"Endpoint error: {str(e)}"}, status_code=500)

@app.local_entrypoint()
async def main_qna():
    # Updated version marker
    print("Deploy Q&A Service: `modal deploy modal_qna_app.py`")
    print("App Name for Modal Service: ai-meeting-qna-service-v2-1-guardrails")