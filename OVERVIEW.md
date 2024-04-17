# AI Runner

This is a technical overview of AI Runner.

This document will provide a high-level overview of the software, its intended usage, and its primary objectives.  It will be updated as the software evolves.

---

AI Runner is an application that empowers people to run AI models on their own hardware. The application utilizes Huggingface libraries to enable users to download models from both Huggingface and Civitai. 
It supports Stable Diffusion and ControlNet models (both finetuned and base), large language models (CausalLM), text-to-speech, speech-to-text, and OCR models.

Upon downloading the software, users are guided through an installation wizard that presents a user agreement, a license agreement, and a Stable Diffusion license agreement.

## Primary Objective

The software provides a safe, offline, and easy AI experience without concerns about government censorship, privacy invasion, data loss, or other issues associated with cloud computing.

Our goal is to develop applications that adhere to the United States Department of Defense standards for AI software while also granting users complete freedom and autonomy over their AI models and data.

## Intended Usage

The application is designed as a standalone tool that can run arbitrary user-supplied AI models to generate AI art and facilitate offline conversations with chatbots, locally on the user's hardware. It is completely free and open-source.

### Secondary Use

The software can also function as a foundational framework for creating further applications in a similar style, inherently equipped with the primary application's core features while offering additional functionalities.

## Stable Diffusion

Image generation with Stable Diffusion models is managed by the LLM and user-entered prompts. The LLM generates suitable prompts based on user requests. 
Negative prompts are predefined and can be adjusted in the settings file.
Users can enter prompts manually and click a generate button for more precise control over image creation.
Users can also use a drawing pad to simultaneously generate images.

## LLMs

The LLM functions as a chatbot that users can customize by assigning a name, personality, mood, custom system prompts, and optional custom guardrails.

Image generation guardrails, used by the image-generating LLM, prevent the production of unethical or potentially harmful/illegal content; these prompts cannot be altered by the user.

## Speech to Text

Users can speak into a microphone, and their speech is transcribed into text for chatbot interactions.

## Text to Speech

Text-to-speech can be activated to allow the chatbot to vocalize text using an AI model.

## Safety Measures and Guardrails

### Stable Diffusion (Image Generation)

The application includes a safety checker model to exclude adult content from images.
This safety checker can be deactivated, but users are warned against this action when they attempt to disable it.

When the safety checker is off, the software discourages unwanted content by removing specific keywords from the prompt and adding them to a negative prompt. These keywords are not removed when the safety checker is active.

### LLM (Text Generation)

The system uses a default prompt that encourages the LLM to be honest, fair, and helpful, alongside a guardrails prompt that deters illegal or false content.

This can be fully customized by the user.

#### Chatbots

Chatbots have shifting moods which are shaped by their personalities and the context of the conversation.

This can be disabled and modified by the user.

## Network

The application operates offline, running locally on the user's machine.
Only the download manager and model manager have internet access.

File operations are strictly controlled, allowing only certain parts of the application to write to the file system, as specified in the application's main.py file, which restricts operations at the system socket level.

## Data Storage

Generated images are stored with optional metadata, which users can disable in the settings. This metadata pertains to the parameters used for image creation.

## Encryption

The file system has not yet been encrypted.
