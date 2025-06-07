# test_secret.py
import os
import modal

app = modal.App(name="test-hf-secret-v2") # New name for new deployment

@app.function(secrets=[modal.Secret.from_name("my-huggingface-secret")])
def check_secret():
    print("--- Checking for HF_TOKEN ---")
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        print(f"SUCCESS: Found HF_TOKEN. Length: {len(hf_token)}. Value starts with: {hf_token[:4]}...")
    else:
        print("ERROR: HF_TOKEN not found in environment variables.")

    print("\n--- Checking for HUGGING_FACE_HUB_TOKEN ---")
    hf_hub_token = os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if hf_hub_token:
        print(f"SUCCESS: Found HUGGING_FACE_HUB_TOKEN. Length: {len(hf_hub_token)}. Value starts with: {hf_hub_token[:4]}...")
    else:
        print("ERROR: HUGGING_FACE_HUB_TOKEN not found in environment variables.")

@app.local_entrypoint()
def main():
    print("Running check_secret.remote()...")
    check_secret.remote()
    print("check_secret.remote() called.")