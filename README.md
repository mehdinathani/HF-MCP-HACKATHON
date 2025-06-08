# 🚀 AI Meeting Assistant Pro (with Q&A) 🚀

**Submission for the Hugging Face Agents & MCP Hackathon 2025 - Track 3: Agentic Demo Showcase**

## Table of Contents
1.  [Introduction](#introduction)
2.  [Features](#features)
3.  [How it Works (Agentic Design)](#how-it-works-agentic-design)
4.  [Tech Stack](#tech-stack)
5.  [Live Demo & Setup](#live-demo--setup)
    *   [Accessing the Live Gradio UI](#accessing-the-live-gradio-ui)
    *   [Running Locally (Optional)](#running-locally-optional)
6.  [MCP (Model Context Protocol) Considerations](#mcp-model-context-protocol-considerations)
7.  [Future Enhancements](#future-enhancements)
8.  [Author](#author)

## Introduction

The AI Meeting Assistant Pro is an intelligent agent designed to alleviate the common pain points of information overload from meetings. By processing meeting transcripts, this tool provides users with concise summaries, extracts key decisions and action items, analyzes overall sentiment, and even allows for follow-up questions on the transcript content. This helps users quickly grasp essential outcomes and stay organized, boosting productivity.

## Features

*   **Automated Meeting Summaries:** Get a concise overview of the main topics and discussions.
*   **Key Decision Extraction:** Clearly identifies important decisions made during the meeting.
*   **Action Item Identification:** Extracts actionable tasks and, where possible, the assigned individuals (output in Markdown for readability).
*   **Sentiment Analysis:** Provides an overall sentiment (Positive, Negative, Neutral) of the meeting with a brief justification.
*   **Follow-up Q&A:** Users can ask specific questions about the content of the provided transcript.
*   **User-Friendly Interface:** Built with Gradio for an intuitive and interactive experience.
*   **Example Transcript & Clear Functionality:** Easy to test and demonstrate.

## How it Works (Agentic Design)

This application demonstrates key agentic behaviors:

1.  **Perception:** The agent "perceives" the meeting content through the user-provided transcript.
2.  **Goal-Oriented Processing:** The primary goal is to distill actionable and understandable insights from the raw transcript. This is broken down into sub-goals:
    *   Summarizing the content.
    *   Identifying decisions.
    *   Extracting action items.
    *   Analyzing sentiment.
    *   Answering user questions based on the transcript.
3.  **Reasoning & Planning (LLM as the Core Engine):**
    *   The backend, powered by Modal, utilizes the `mistralai/Mistral-7B-Instruct-v0.2` Large Language Model (LLM).
    *   For each sub-goal (summarize, decide, etc.), carefully crafted prompts are sent to the LLM. These prompts guide the LLM's "reasoning" process to extract the specific type of information required. This mimics an agent planning how to tackle different aspects of a complex task.
4.  **Action & Response:** The agent "acts" by generating the structured insights (summary, decisions, actions, sentiment, Q&A answers) and presenting them back to the user through the Gradio interface.

The system is architected with a Gradio frontend (`app.py`) that communicates with two distinct serverless Modal backends: one for comprehensive insights (`modal_insights_app.py`) and another specialized for Q&A (`modal_qna_app.py`). This separation ensures clarity and robustness.

## Tech Stack

*   **Frontend UI:** Gradio
*   **Backend AI Logic & LLM Hosting:** Modal (serverless platform)
    *   Utilizes Modal's GPU instances (A10G) for LLM inference.
    *   Exposes functionality via FastAPI web endpoints.
*   **Large Language Model (LLM):** `mistralai/Mistral-7B-Instruct-v0.2` (via Hugging Face `transformers` library)
*   **Core Language:** Python
*   **Supporting Libraries:** `requests` (for frontend-backend communication)

## Live Demo & Setup

### Accessing the Live Gradio UI

*   **Live Demo URL:** [YOUR_HUGGING_FACE_SPACE_URL_HERE] *(You will fill this in after deploying to HF Spaces)*

### Running Locally (Optional)

1.  **Clone the Repository:**
    ```bash
    git clone [YOUR_GITHUB_REPO_URL_HERE]
    cd [YOUR_REPO_NAME]
    ```
2.  **Set up Python Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install Dependencies for Gradio App:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Deploy Modal Backends:**
    *   Ensure you have Modal CLI installed and configured (`pip install modal-client; modal token new`).
    *   Ensure you have a Hugging Face token stored as a Modal secret named `my-huggingface-secret` with a key `HF_TOKEN`.
    *   Deploy the insights service:
        ```bash
        modal deploy modal_insights_app.py
        ```
    *   Deploy the Q&A service:
        ```bash
        modal deploy modal_qna_app.py
        ```
    *   Note the two distinct endpoint URLs provided by Modal after deployment.
5.  **Configure Endpoints in `app.py`:**
    *   Open `app.py`.
    *   Update `MODAL_INSIGHTS_ENDPOINT_URL` with the URL from deploying `modal_insights_app.py`.
    *   Update `MODAL_QNA_ENDPOINT_URL` with the URL from deploying `modal_qna_app.py`.
6.  **Run the Gradio Application:**
    ```bash
    python app.py
    ```
    The application will be available at a local URL (e.g., `http://127.0.0.1:7860`).

## MCP (Model Context Protocol) Considerations

While this project does not implement a full MCP server, its design aligns with MCP principles by emphasizing structured communication and clear context/result handling:

1.  **Structured Context Input:** The Gradio UI sends the transcript (and questions for Q&A) to the Modal backends as structured JSON payloads. This is analogous to how an MCP `UserMessage` might carry primary text content.

2.  **Agentic Backend Processing:** The Modal services act as intelligent agent backends. They receive context and perform distinct analytical tasks using the LLM, guided by specific prompts. This mirrors how an MCP-enabled agent processes information based on its goals and available tools/skills.

3.  **Structured Result Output:** The Modal services return consistent JSON structures for insights and Q&A answers. This allows the Gradio client to reliably parse and display the agent's findings, similar to how an MCP `AssistantMessage` might contain structured content blocks.

4.  **Potential for MCP Integration:**
    *   The existing JSON request/response formats could be mapped to formal MCP message types.
    *   An MCP server could potentially orchestrate communication between the Gradio UI (or other clients) and the Modal services. The Modal services would then act as specialized "skills" or "tools" callable via MCP. This would enhance interoperability, allowing other MCP-compliant systems to leverage this meeting analysis agent.

This project demonstrates a practical application of agentic AI, with a foundation suitable for future integration into a broader MCP-compliant ecosystem.

## Future Enhancements

*   **Multi-turn Q&A:** Implement conversation history for more natural follow-up questions.
*   **Tool Use for External Data:** Allow the agent to fetch related documents or calendar information.
*   **Speaker Diarization:** If transcripts could identify speakers, insights could be attributed.
*   **Direct Audio Input:** Integrate speech-to-text for direct audio processing.
*   **More Sophisticated Guardrails:** Beyond prompt-based, explore techniques for fact-checking or limiting off-topic generation.

## Author

*   **Name:** [Your Name / Your HF Username]
*   **Hugging Face Profile:** [Link to Your HF Profile]
*   **GitHub Repository:** [Link to Your Project's GitHub Repo]