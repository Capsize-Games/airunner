# AI Runner - Privacy Policy

**Last Updated: November 30, 2025**

**Effective Date: November 30, 2025**

Capsize LLC ("Capsize," "we," "us," or "our"), a Colorado limited liability company, is committed to protecting your privacy. This Privacy Policy explains how the AI Runner software ("Software") handles information when you use it.

## 1. Overview: Privacy by Design

AI Runner is designed with privacy as a core principle. **The Software runs entirely on your local machine.** We do not operate servers that collect, store, or process your personal data. Your data stays on your device unless you explicitly choose to use third-party services.

## 2. Information We Do NOT Collect

Capsize LLC does **not** collect:

* Personal identification information (name, email, address, phone number)
* Usage data or analytics
* Chat conversations or prompts you enter
* Images, documents, or files you process
* Voice recordings or biometric data
* Location data
* Device identifiers or fingerprints
* Browsing history or search queries

## 3. Data Processed Locally on Your Device

The Software processes the following types of data **locally on your device only**:

### 3.1 Chat and Text Data
* Conversations with AI assistants are processed and stored locally
* Prompts, responses, and conversation history remain on your device
* RAG (Retrieval-Augmented Generation) document processing occurs locally

### 3.2 Image Data
* Images you generate or process are stored locally
* Image prompts and settings are stored locally
* No images are transmitted to external servers by default

### 3.3 Voice and Audio Data
* Voice recordings for speech-to-text are processed locally
* Text-to-speech audio is generated locally
* Voice samples for voice cloning (if used) remain on your device

### 3.4 Biometric Data
* Voice characteristics used for speech processing
* This data is never transmitted externally and is processed solely for Software functionality

### 3.5 Application Settings
* User preferences and configurations
* Window positions and UI customizations
* Model selections and parameters

## 4. Third-Party Services and External Connections

### 4.1 AI Model Downloads
When you download AI models using the built-in model downloader, your computer connects directly to third-party repositories:

* **HuggingFace:** When downloading LLM, STT, TTS, and Stable Diffusion models
* **CivitAI:** When downloading community models, LoRAs, or embeddings via the CivitAI downloader

These services may log your IP address and download requests according to their own privacy policies:
* **Hugging Face:** https://huggingface.co/privacy
* **CivitAI:** https://civitai.com/content/privacy

### 4.2 Search Features
If you enable search functionality, the following connections may be made:

* **DuckDuckGo API:** When using web search features, your search queries are transmitted to DuckDuckGo's servers
* **Deep Research:** When using the Deep Research feature, the LLM will search DuckDuckGo and scrape web pages for results to augment its responses, which involves connecting to DuckDuckGo's servers and the individual websites being researched

### 4.3 External LLM Providers
If you configure external LLM providers, your prompts and conversations will be transmitted to those services:

* **OpenRouter:** If configured, your prompts are sent to OpenRouter's API servers
* **OpenAI:** If configured, your prompts are sent to OpenAI's API servers
* **Ollama:** If configured with a remote server, data is sent to that server

### 4.4 Weather Information
If you enable the weather prompt feature in the LLM settings, your location coordinates are transmitted to the Open-Meteo weather service:

* **Open-Meteo API:** Your latitude and longitude (derived from your zipcode setting) are sent to `api.open-meteo.com` to retrieve current weather conditions
* **Data Sent:** Only geographic coordinates—no personal identifiers
* **Privacy Policy:** https://open-meteo.com/en/terms

This feature is **disabled by default** and only activates when you:
1. Enable "Use weather prompt" in LLM settings
2. Provide your location (zipcode or coordinates) in user settings

### 4.5 Privacy Recommendation
**We recommend using a VPN** when using features that connect to external services (model downloads, web search, Deep Research, weather, or external LLM providers) if you want additional privacy protection.

### 4.6 Local-First Design
By default, AI Runner operates entirely locally without any external connections. External connections only occur when you:
* Download models from HuggingFace or CivitAI
* Use web search or Deep Research features
* Enable the weather prompt feature
* Configure external LLM providers (OpenRouter, OpenAI, remote Ollama)

You can use AI Runner with full functionality by downloading models once and then operating completely offline.

## 5. Data Storage and Security

### 5.1 Local Storage
All data is stored in your local application directory (typically `~/.local/share/airunner/` on Linux). This includes:

* SQLite databases for settings and metadata
* Generated images and media files
* Downloaded AI models
* Conversation logs and history

### 5.2 Your Responsibility
Since all data is stored locally, you are responsible for:

* Securing your device and the Software's data directory
* Creating backups of important data
* Deleting data you no longer wish to retain

### 5.3 Data Deletion
You can delete all Software data by:

* Using the application's built-in data management features
* Manually deleting the application data directory
* Uninstalling the Software

## 6. Colorado Privacy Act (CPA) Compliance

As a Colorado company, we are committed to compliance with the Colorado Privacy Act. Under the CPA, you have certain rights regarding your personal data:

### 6.1 Your Rights
* **Right to Access:** You can access all your data directly on your device
* **Right to Correct:** You can modify your data through the Software's settings
* **Right to Delete:** You can delete your data at any time
* **Right to Data Portability:** Your data is stored in standard formats on your device
* **Right to Opt-Out:** Since we don't collect data, there's nothing to opt out of

### 6.2 Sensitive Data
The Software may process data considered "sensitive" under the CPA, including:

* Biometric data (voice characteristics)
* Data revealing certain personal characteristics through AI profiling features

By using these features, you consent to their local processing. You can disable these features at any time through the Software's settings.

## 7. Children's Privacy

AI Runner is not intended for use by individuals under 18 years of age. We do not knowingly collect or process information from children. If you believe a child has used this Software, please ensure all locally stored data is deleted.

## 8. International Users

If you are using the Software from outside the United States, please be aware that your data remains on your local device and is not transferred to us. However, if you use third-party services (like model providers), data may be transferred according to their policies.

## 9. Changes to This Privacy Policy

We may update this Privacy Policy from time to time. Changes will be indicated by updating the "Last Updated" date. Your continued use of the Software after any changes constitutes acceptance of the updated Privacy Policy.

## 10. Open Source Transparency

AI Runner is open-source software. You can review our source code at any time to verify our privacy practices:

* **Repository:** https://github.com/Capsize-Games/airunner

## 11. Contact Us

If you have questions about this Privacy Policy or our privacy practices, please contact us:

**Capsize LLC**
Email: contact@capsizegames.com

## 12. Summary

| What | How It's Handled |
|------|------------------|
| Personal Data Collection | None - we don't collect any |
| Data Storage | Local device only |
| Data Sharing | None by default - your data stays on your device |
| Analytics/Tracking | None |
| Model Downloads | Connects to HuggingFace/CivitAI (user-initiated) |
| Web Search/Deep Research | Connects to DuckDuckGo and websites (user-enabled) |
| External LLM Providers | Connects to OpenRouter/OpenAI (user-configured) |
| Data Deletion | Full control - delete anytime |
