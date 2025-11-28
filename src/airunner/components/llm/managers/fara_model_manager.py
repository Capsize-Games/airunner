"""
Fara-7B Model Manager for Computer Use Agent.

This module provides a specialized model manager for Microsoft's Fara-7B,
an efficient agentic model designed for computer use. Fara-7B is based on
Qwen 2.5-VL and takes screenshots + text context as input, predicting
thoughts and actions with grounded arguments.

Key Features:
- Screenshot-based computer interaction
- Chain-of-thought reasoning followed by tool calls
- Critical point recognition for safe automation
- Actions: click, type, scroll, visit_url, web_search, etc.

Usage:
    manager = FaraModelManager()
    manager.load()
    action = manager.get_next_action(screenshot, goal, history)
"""

import os
from pathlib import Path
from typing import Dict, Optional, Any, List, Union
import base64
import io

import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
from transformers import BitsAndBytesConfig

from airunner.components.llm.managers.llm_model_manager import LLMModelManager
from airunner.components.llm.managers.llm_request import LLMRequest
from airunner.settings import AIRUNNER_BASE_PATH
from airunner.enums import LLMActionType, ModelType, ModelStatus, SignalCode


# Fara repo ID for HuggingFace downloads
FARA_REPO_ID = "microsoft/Fara-7B"

# Default local path for Fara model
DEFAULT_FARA_MODEL_PATH = os.path.join(
    AIRUNNER_BASE_PATH,
    "text",
    "models",
    "llm",
    "fara",
    "Fara-7B"
)

# Fara's system prompt with computer use function signature
# Extended to support both web and general desktop automation
# NOTE: All literal curly braces in JSON are doubled ({{ }}) for Python .format() compatibility
FARA_SYSTEM_PROMPT = """You are a computer automation agent that performs actions on a desktop computer to fulfill user requests by calling various tools.

You can interact with:
- Web browsers (navigate, search, fill forms, click links)
- Desktop applications (open apps, interact with windows, menus)
- Files and folders (through GUI interactions)
- Any graphical interface visible on screen

HOW TO RECOGNIZE AN OPEN APPLICATION:
1. An open application will appear as a LARGE WINDOW in the CENTER of the screen
2. The taskbar icon will look highlighted or underlined when the app is open
3. Firefox/browser window: Large area covering most of screen, with toolbar at TOP (URL bar, tabs, buttons)
4. If you see a large window - the application IS open. Do NOT click on the taskbar icon again.
5. The URL/address bar in Firefox is at the TOP of the browser window, approximately y=60-100 pixels

HOW TO NAVIGATE TO A URL IN A BROWSER:
1. If browser is not open (no large window visible), click on the browser icon to open it
2. Once the browser window is visible (large window on screen), click on the URL/address bar at the TOP of the browser window - coordinates around (center_x, 80)
3. Use the "type" action to enter the URL
4. Use the "key" action with ["Enter"] to navigate

AFTER CLICKING TO OPEN AN APPLICATION:
1. The application window should now be visible as a large area on screen
2. DO NOT click on the taskbar icon again
3. Instead, interact with the application window that is now open
4. For browsers: click on the URL bar at the TOP of the window (y around 60-100)

HOW TO TYPE TEXT:
1. First click on the text field or input area where you want to type
2. Then use the "type" action with your text
3. The coordinate parameter for "type" is optional if you already clicked

CRITICAL RULES FOR ACTION SELECTION:
1. NEVER repeat the exact same action twice in a row. If you already clicked somewhere, look at the current screenshot to see what changed.
2. ALWAYS analyze the current screenshot carefully. If an application is already open, do NOT click on its icon again.
3. If a previous action seems to have had no effect, try a DIFFERENT approach (different coordinates, different action type, or interact with what's currently visible).
4. Your "Previous actions" history shows what you already did - use it to avoid repetition.
5. Focus on what is CURRENTLY visible in the screenshot, not what you expect to see.
6. After clicking to open an application, WAIT for it to appear before taking the next action.

You should stop execution at Critical Points. A Critical Point occurs in tasks like:

• Checkout / Purchase / Payment
• Book / Reserve
• Call / Email / Message
• Order / Subscribe
• Login with credentials
• Form submission with personal data

A Critical Point requires the user's permission or personal/sensitive information (name, email, credit card, address, payment information, resume, etc.) to complete a transaction, or to communicate as a human would.

Guideline: Solve the task as far as possible up until a Critical Point.

Examples:

• If the task is to "call a restaurant to make a reservation," do not actually make the call. Instead, navigate to the restaurant's page and find the phone number.
• If the task is to "order new size 12 running shoes," do not place the order. Instead, search for the right shoes that meet the criteria and add them to the cart.
• If the task is to "open LibreOffice and create a document," open the application and create the document, stopping before saving with sensitive content.

Some tasks, like answering questions or organizing files, may not encounter a Critical Point at all.

Function Signatures:

You are provided with function signatures within XML tags:

{{
  "type": "function",
  "function": {{
    "name": "computer_use",
    "description": "Use a mouse and keyboard to interact with a computer, and take screenshots.\\n* This is an interface to a desktop GUI. You can interact with any visible application.\\n* Click on desktop icons or taskbar to start applications.\\n* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions.\\n* The screen's resolution is {screen_width}x{screen_height}.\\n* Whenever you intend to move the cursor to click on an element, consult the screenshot to determine the coordinates.\\n* If clicking on an element fails, try adjusting your cursor position.",
    "parameters": {{
      "properties": {{
        "action": {{
          "description": "The action to perform. The available actions are:\\n* key: Performs key down presses on the arguments passed in order, then performs key releases in reverse order. Includes 'Enter', 'Alt', 'Shift', 'Tab', 'Control', 'Backspace', 'Delete', 'Escape', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'PageDown', 'PageUp', etc.\\n* type: Type a string of text on the keyboard.\\n* mouse_move: Move the cursor to a specified (x, y) pixel coordinate on the screen.\\n* left_click: Click the left mouse button.\\n* right_click: Click the right mouse button (for context menus).\\n* double_click: Double-click the left mouse button (for opening files/folders).\\n* drag: Drag from one coordinate to another.\\n* scroll: Performs a scroll of the mouse scroll wheel.\\n* hotkey: Execute a keyboard shortcut (e.g., Ctrl+S, Alt+Tab).\\n* open_application: Open an application by name.\\n* visit_url: Visit a specified URL in browser.\\n* web_search: Perform a web search with a specified query.\\n* history_back: Go back to the previous page in the browser history.\\n* pause_and_memorize_fact: Remember an important fact for later use.\\n* wait: Wait for a specified amount of time.\\n* terminate: End the task with success or failure status.",
          "enum": ["key", "type", "mouse_move", "left_click", "right_click", "double_click", "drag", "scroll", "hotkey", "open_application", "visit_url", "web_search", "history_back", "pause_and_memorize_fact", "wait", "terminate"],
          "type": "string"
        }},
        "keys": {{"description": "Required by action=key and action=hotkey. Array of key names.", "type": "array"}},
        "text": {{"description": "Required only by action=type.", "type": "string"}},
        "coordinate": {{"description": "(x, y) coordinates for mouse actions. Required by action=left_click, action=right_click, action=double_click, action=mouse_move, and action=type.", "type": "array"}},
        "start_coordinate": {{"description": "Starting (x, y) coordinates. Required only by action=drag.", "type": "array"}},
        "end_coordinate": {{"description": "Ending (x, y) coordinates. Required only by action=drag.", "type": "array"}},
        "pixels": {{"description": "Amount of scrolling. Positive = up, Negative = down. Required only by action=scroll.", "type": "number"}},
        "url": {{"description": "The URL to visit. Required only by action=visit_url.", "type": "string"}},
        "query": {{"description": "The query to search for. Required only by action=web_search.", "type": "string"}},
        "application": {{"description": "Application name to open. Required only by action=open_application.", "type": "string"}},
        "fact": {{"description": "The fact to remember for the future. Required only by action=pause_and_memorize_fact.", "type": "string"}},
        "time": {{"description": "Seconds to wait. Required only by action=wait.", "type": "number"}},
        "status": {{"description": "Status of the task. Required only by action=terminate.", "type": "string", "enum": ["success", "failure"]}}
      }},
      "required": ["action"],
      "type": "object"
    }}
  }}
}}

For each function call, return a JSON object with the function name and arguments within XML tags:

```json
{{
  "name": "<function-name>",
  "arguments": <args-json-object>
}}
```
"""


class FaraModelManager(LLMModelManager):
    """
    Handler for Microsoft's Fara-7B computer use agent.

    This class extends LLMModelManager to provide specialized handling for
    Fara-7B, which is based on Qwen 2.5-VL and designed for computer use
    tasks like web automation.

    The model takes:
    - Screenshots of the current screen state
    - User's goal/task description
    - History of previous actions (thoughts + actions)

    And outputs:
    - Chain-of-thought reasoning
    - Tool call with action and arguments
    """

    _processor = None  # Qwen2.5-VL processor for text + image
    _model = None  # Qwen2_5_VLForConditionalGeneration instance
    
    # Actual screen resolution - set by controller
    _screen_width: int = 1920
    _screen_height: int = 1080
    _action_history: List[Dict[str, Any]] = []
    _memorized_facts: List[str] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.debug("Initializing FaraModelManager")
        self._action_history = []
        self._memorized_facts = []

    @property
    def model_path(self) -> str:
        """
        Get the path to the Fara model.

        Returns:
            str: Path to the local model directory
        """
        model_version = getattr(self, '_fara_model_path', None)
        if not model_version:
            model_version = DEFAULT_FARA_MODEL_PATH

        return os.path.expanduser(model_version)

    @model_path.setter
    def model_path(self, value: str) -> None:
        """Set the Fara model path."""
        self._fara_model_path = value

    @property
    def supports_vision(self) -> bool:
        """Fara-7B supports vision inputs (screenshots)."""
        return True

    @property
    def screen_resolution(self) -> tuple:
        """Get the screen resolution for coordinate mapping."""
        return (self._screen_width, self._screen_height)

    def set_screen_resolution(self, width: int, height: int) -> None:
        """Set the screen resolution for accurate coordinate mapping."""
        self._screen_width = width
        self._screen_height = height
        self.logger.info(f"Screen resolution set to {width}x{height}")

    def load(self) -> None:
        """
        Load the Fara model with download check.

        Overrides parent to use Fara-specific model checking and download.
        """
        self.logger.info(f"Fara load() called, current status: {self.model_status.get(ModelType.LLM, ModelStatus.UNLOADED)}")

        if self.model_status.get(ModelType.LLM) in (
            ModelStatus.LOADING,
            ModelStatus.LOADED,
        ):
            self.logger.info("Fara model already loading or loaded")
            return

        # Check if model exists, trigger download if needed
        if not self._check_fara_model_exists():
            self._trigger_fara_download()
            return

        self.change_model_status(ModelType.LLM, ModelStatus.LOADING)

        try:
            self._load_tokenizer()
            self._load_model()

            if self._model is not None and self._processor is not None:
                self.change_model_status(ModelType.LLM, ModelStatus.LOADED)
                self.logger.info("Fara model loaded successfully")
            else:
                self.change_model_status(ModelType.LLM, ModelStatus.FAILED)
                self.logger.error("Fara model failed to load")
        except Exception as e:
            self.logger.error(f"Error loading Fara model: {e}")
            self.change_model_status(ModelType.LLM, ModelStatus.FAILED)

    def _check_fara_model_exists(self) -> bool:
        """
        Check if the Fara model exists locally.

        Returns:
            True if model files exist, False otherwise.
        """
        model_path = self.model_path

        # Check local path only - we don't use HuggingFace hub
        if not os.path.exists(model_path):
            self.logger.info(f"Fara model path does not exist: {model_path}")
            return False

        # Check for essential files including model weights
        essential_files = ["config.json", "preprocessor_config.json"]
        
        try:
            files_in_dir = os.listdir(model_path)
        except Exception as e:
            self.logger.warning(f"Error listing model directory: {e}")
            return False
            
        has_model_weights = any(
            f.endswith(".safetensors") or f.endswith(".bin")
            for f in files_in_dir
        )
        has_config = all(
            os.path.exists(os.path.join(model_path, f))
            for f in essential_files
        )
        
        if not has_model_weights:
            self.logger.info("Fara model missing weight files (.safetensors or .bin)")
            return False
        if not has_config:
            self.logger.info("Fara model missing config files")
            return False
            
        self.logger.info(f"Fara model found at {model_path}")
        return True

    def _trigger_fara_download(self) -> None:
        """
        Trigger download of the Fara model via the custom download system.
        """
        self.logger.info(f"Triggering Fara model download: {FARA_REPO_ID}")

        signal_data = {
            "model_path": self.model_path,
            "model_name": "Fara-7B",
            "repo_id": FARA_REPO_ID,
            "model_type": "fara",
        }

        self.emit_signal(SignalCode.FARA_MODEL_DOWNLOAD_REQUIRED, signal_data)
        self.change_model_status(ModelType.LLM, ModelStatus.FAILED)

    def _get_quantization_config(self) -> Optional[BitsAndBytesConfig]:
        """Get 4-bit quantization config for memory efficiency."""
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    def _get_quantized_model_path(self) -> str:
        """
        Get the path for the pre-quantized Fara model.

        Returns:
            str: Path to quantized model directory (e.g., Fara-7B-4bit/)
        """
        base_path = self.model_path
        base_dir = os.path.dirname(base_path)
        model_name = os.path.basename(base_path)
        return os.path.join(base_dir, f"{model_name}-4bit")

    def _check_quantized_model_exists(self) -> bool:
        """
        Check if a pre-quantized Fara model exists and is valid.

        Returns:
            bool: True if quantized model exists and appears valid
        """
        quant_path = self._get_quantized_model_path()
        
        if not os.path.exists(quant_path):
            return False

        try:
            required_files = ["config.json"]
            has_model = any(
                f.endswith((".safetensors", ".bin"))
                for f in os.listdir(quant_path)
            )
            has_config = all(
                os.path.exists(os.path.join(quant_path, f))
                for f in required_files
            )
            return has_model and has_config
        except Exception as e:
            self.logger.warning(f"Error checking quantized model: {e}")
            return False

    def _save_quantized_model(self) -> None:
        """
        Save the currently loaded quantized model to disk for faster future loads.
        
        This combines the sharded safetensors into a single quantized model file.
        """
        if self._model is None:
            return
            
        quant_path = self._get_quantized_model_path()
        
        if self._check_quantized_model_exists():
            self.logger.info(f"Quantized model already exists at {quant_path}")
            return
        
        try:
            import shutil
            
            os.makedirs(quant_path, exist_ok=True)
            self.logger.info(f"Saving 4-bit quantized Fara model to {quant_path}")
            
            # Save the model weights
            self._model.save_pretrained(
                quant_path, 
                safe_serialization=True,
                max_shard_size="10GB"  # Large shard to combine into fewer files
            )
            
            # Copy processor/tokenizer files from original local model
            source_path = self.model_path
            tokenizer_files = [
                "tokenizer.json",
                "tokenizer_config.json", 
                "special_tokens_map.json",
                "added_tokens.json",
                "merges.txt",
                "vocab.json",
                "preprocessor_config.json",
                "chat_template.jinja",
                "generation_config.json",
                "video_preprocessor_config.json",
            ]
            for filename in tokenizer_files:
                src = os.path.join(source_path, filename)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(quant_path, filename))
            
            self.logger.info(
                f"✓ 4-bit quantized Fara model saved successfully to {quant_path}. "
                "Future loads will use this saved version for faster startup."
            )
        except Exception as e:
            self.logger.warning(f"Could not save quantized model: {e}")

    def _load_tokenizer(self) -> None:
        """
        Load the AutoProcessor for Qwen2.5-VL based Fara model.

        The processor handles both text and image inputs.
        Uses pre-quantized path if available.
        """
        if self._processor is not None:
            return

        # Try pre-quantized path first
        load_path = self.model_path
        if self._check_quantized_model_exists():
            load_path = self._get_quantized_model_path()
            self.logger.debug(f"Loading Fara processor from pre-quantized path: {load_path}")
        else:
            self.logger.debug(f"Loading Fara processor from {load_path}")
            
        try:
            # Load from local path - we don't use HuggingFace hub
            self._processor = AutoProcessor.from_pretrained(
                load_path,
                local_files_only=True,
                trust_remote_code=True,
            )
            self._tokenizer = self._processor  # For compatibility
            self.logger.debug("Fara processor loaded successfully")
        except Exception as e:
            import traceback
            self.logger.error(f"Error loading Fara processor: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.logger.error(f"load_path was: '{load_path}'")
            self._processor = None
            self._tokenizer = None

    def _load_model(self) -> None:
        """
        Load the Fara-7B model with optional quantization.
        
        First checks for a pre-quantized model. If not found, loads with
        runtime quantization and saves the quantized model for future use.
        """
        if self._model is not None:
            return

        # Check for pre-quantized model first
        use_pre_quantized = self._check_quantized_model_exists()
        
        if use_pre_quantized:
            load_path = self._get_quantized_model_path()
            self.logger.info(f"Loading pre-quantized Fara model from {load_path}")
            try:
                # Pre-quantized model - don't pass quantization_config
                self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                    load_path,
                    local_files_only=True,  # Always local for pre-quantized
                    trust_remote_code=True,
                    device_map="auto",
                    torch_dtype=torch.bfloat16,
                ).eval()
                self.logger.info("✓ Pre-quantized Fara-7B model loaded successfully")
                return
            except Exception as e:
                import traceback
                self.logger.warning(f"Failed to load pre-quantized model: {e}")
                self.logger.warning(f"Full traceback: {traceback.format_exc()}")
                self.logger.info("Falling back to runtime quantization...")

        # Load with runtime quantization from local path
        self.logger.debug(f"Loading Fara model from {self.model_path}")
        try:
            quantization_config = self._get_quantization_config()

            self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_path,
                local_files_only=True,  # Always local - we don't use HuggingFace hub
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                quantization_config=quantization_config,
            ).eval()
            self.logger.info("Fara-7B model loaded successfully (4-bit quantized)")
            
            # Save quantized model for faster future loads
            self._save_quantized_model()
            
        except Exception as e:
            import traceback
            self.logger.error(f"Error loading Fara model: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            self.logger.error(f"model_path was: '{self.model_path}'")
            self._model = None

    def _prepare_image(self, image: Union[str, bytes, Image.Image]) -> Image.Image:
        """
        Convert various image formats to PIL Image.
        
        Note: We pass the image at native resolution. The Qwen2.5-VL processor
        handles any necessary resizing internally, and the model outputs
        coordinates in the original image's resolution.

        Args:
            image: Can be file path, base64 bytes, or PIL Image

        Returns:
            PIL Image object
        """
        if isinstance(image, Image.Image):
            return image
        elif isinstance(image, bytes):
            return Image.open(io.BytesIO(image))
        elif isinstance(image, str):
            if os.path.exists(image):
                return Image.open(image)
            elif image.startswith("data:image"):
                # Base64 data URL
                base64_data = image.split(",")[1]
                return Image.open(io.BytesIO(base64.b64decode(base64_data)))
            else:
                # Assume it's base64
                return Image.open(io.BytesIO(base64.b64decode(image)))
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt with actual screen resolution."""
        return FARA_SYSTEM_PROMPT.format(
            screen_width=self._screen_width,
            screen_height=self._screen_height,
        )

    def _build_history_text(self) -> str:
        """Build text representation of action history."""
        if not self._action_history:
            return ""

        history_parts = []
        for i, entry in enumerate(self._action_history):
            thought = entry.get("thought", "")
            action = entry.get("action", {})
            history_parts.append(f"Step {i+1}:")
            if thought:
                history_parts.append(f"Thought: {thought}")
            if action:
                history_parts.append(f"Action: {action}")
            history_parts.append("")

        return "\n".join(history_parts)

    def _build_facts_text(self) -> str:
        """Build text representation of memorized facts."""
        if not self._memorized_facts:
            return ""

        return "Memorized facts:\n" + "\n".join(
            f"- {fact}" for fact in self._memorized_facts
        )

    def _format_qwen_chat(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format messages for Qwen2.5-VL chat format manually.
        
        Qwen2.5-VL uses a specific format:
        <|im_start|>system
        {system_message}<|im_end|>
        <|im_start|>user
        {user_message}<|im_end|>
        <|im_start|>assistant
        
        Args:
            messages: List of message dicts with role and content
            
        Returns:
            Formatted prompt string
        """
        formatted_parts = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Handle content that might be a list (multimodal)
            if isinstance(content, list):
                # Extract text parts, images handled separately by processor
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif item.get("type") == "image":
                            text_parts.append("<|vision_start|><|image_pad|><|vision_end|>")
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = "\n".join(text_parts)
            
            formatted_parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        
        # Add assistant prompt for generation
        formatted_parts.append("<|im_start|>assistant\n")
        
        return "\n".join(formatted_parts)

    def get_next_action(
        self,
        screenshot: Union[str, bytes, Image.Image],
        goal: str,
        additional_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get the next action to perform based on current screenshot and goal.

        Args:
            screenshot: Current screen state (file path, bytes, or PIL Image)
            goal: The user's task/goal description
            additional_context: Optional additional context

        Returns:
            Dictionary with 'thought' and 'action' keys
        """
        if self._model is None or self._processor is None:
            self.logger.error("Model not loaded. Call load() first.")
            return {"error": "Model not loaded"}

        # Prepare image
        image = self._prepare_image(screenshot)

        # Build the conversation
        system_prompt = self._build_system_prompt()
        history_text = self._build_history_text()
        facts_text = self._build_facts_text()
        
        self.logger.debug(f"Action history count: {len(self._action_history)}")
        if history_text:
            self.logger.debug(f"History text (first 500 chars): {history_text[:500]}")

        # Detect repeated actions and add strong guidance
        repetition_warning = ""
        if len(self._action_history) >= 2:
            last_action = self._action_history[-1].get("action", {})
            prev_action = self._action_history[-2].get("action", {})
            if last_action == prev_action:
                last_action_type = last_action.get("action", "")
                self.logger.warning(f"Detected repeated action: {last_action}")
                
                # Provide specific guidance based on what was repeated
                if last_action_type == "left_click":
                    # Check if the goal mentions a URL or website
                    goal_lower = goal.lower()
                    if any(word in goal_lower for word in ["url", "navigate", "http", ".com", ".org", ".net", "website", "reddit", "google", "facebook"]):
                        repetition_warning = """
⚠️ CRITICAL: You already clicked to open the browser. The browser is NOW OPEN.
Your NEXT action MUST be one of these:
1. Click on the URL/address bar at the TOP of the browser window (usually around y=80-120)
2. Then use "type" action with the URL

DO NOT click on the taskbar icon again. Look at the TOP of the screen for the browser window.
The address bar is typically a white text field near the top of the browser.
"""
                    else:
                        repetition_warning = """
⚠️ CRITICAL: You clicked the same location twice. The application should now be open.
DO NOT click again. Look at the current screenshot carefully.
If a browser window is visible, click on the URL/address bar and type the URL.
If the goal involves typing, use the "type" action now.
"""
                else:
                    repetition_warning = "\n⚠️ WARNING: You repeated the same action. You MUST try a DIFFERENT action now.\n"

        # Build user message
        user_content = f"Goal: {goal}\n"
        if facts_text:
            user_content += f"\n{facts_text}\n"
        if history_text:
            user_content += f"\nPrevious actions:\n{history_text}\n"
        if repetition_warning:
            user_content += repetition_warning
        if additional_context:
            user_content += f"\nAdditional context: {additional_context}\n"
        user_content += "\nCurrent screenshot is attached. What is the next action?"

        # Format messages for Qwen2.5-VL
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": user_content},
                ],
            },
        ]

        # Process inputs - use tokenizer for chat template if processor doesn't have one
        text = None
        
        # Try processor first
        try:
            text = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except (ValueError, AttributeError) as e:
            self.logger.debug(f"Processor chat template failed: {e}")
        
        # Try tokenizer if processor failed
        if text is None:
            try:
                if hasattr(self._processor, 'tokenizer') and hasattr(self._processor.tokenizer, 'apply_chat_template'):
                    text = self._processor.tokenizer.apply_chat_template(
                        messages, tokenize=False, add_generation_prompt=True
                    )
            except (ValueError, AttributeError) as e:
                self.logger.debug(f"Tokenizer chat template failed: {e}")
        
        # Fall back to manual formatting
        if text is None:
            self.logger.debug("Using manual Qwen chat formatting")
            text = self._format_qwen_chat(messages)
        
        inputs = self._processor(
            text=[text],
            images=[image],
            return_tensors="pt",
            padding=True,
        ).to(self._model.device)

        # Increase temperature if repetition detected to encourage different responses
        temperature = 0.7 if repetition_warning else 0.1
        if repetition_warning:
            self.logger.info(f"Increasing temperature to {temperature} due to repetition")

        # Generate response
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=True,
                temperature=temperature,
                top_p=0.9,
            )

        # Decode response
        response = self._processor.batch_decode(
            outputs[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )[0]

        # Parse the response
        result = self._parse_response(response)
        
        # Log the parsed action for debugging
        action = result.get("action", {})
        thought = result.get("thought", "")[:100]
        self.logger.info(f"Fara thought: {thought}...")
        self.logger.info(f"Fara action: {action}")

        # Update history
        self._action_history.append(result)

        # Handle memorize_fact action
        if result.get("action", {}).get("action") == "pause_and_memorize_fact":
            fact = result["action"].get("fact", "")
            if fact:
                self._memorized_facts.append(fact)

        return result

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse Fara's response into thought and action.

        Args:
            response: Raw model output

        Returns:
            Dictionary with 'thought' and 'action' keys
        """
        import json
        import re

        result = {"thought": "", "action": {}, "raw_response": response}

        # Try multiple patterns to extract JSON

        # Pattern 0: Handle "Action: {...}" format with Python dict syntax (single quotes)
        # The model sometimes outputs: Action: {'action': 'left_click', 'coordinate': [x, y]}
        action_match = re.search(r'Action:\s*(\{.*?\})\}*', response, re.DOTALL)
        if action_match:
            dict_str = action_match.group(1)
            # Fix trailing braces - only keep the matched group
            thought = response[:action_match.start()].strip()
            result["thought"] = thought
            
            # Convert Python dict syntax to JSON (single quotes to double quotes)
            try:
                # First try as-is (might be valid JSON)
                action_data = json.loads(dict_str)
                result["action"] = action_data
                return result
            except json.JSONDecodeError:
                # Try converting single quotes to double quotes
                try:
                    # Replace single quotes with double quotes (careful with nested strings)
                    json_str = dict_str.replace("'", '"')
                    action_data = json.loads(json_str)
                    result["action"] = action_data
                    return result
                except json.JSONDecodeError as e:
                    self.logger.debug(f"Failed to parse Action dict: {e}")

        # Pattern 1: JSON in markdown code block
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            thought = response[:json_match.start()].strip()
            result["thought"] = thought

            try:
                action_data = json.loads(json_str)
                if "arguments" in action_data:
                    result["action"] = action_data["arguments"]
                else:
                    result["action"] = action_data
                return result
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse markdown JSON: {e}")

        # Pattern 2: JSON in generic code block
        json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            thought = response[:json_match.start()].strip()
            result["thought"] = thought

            try:
                action_data = json.loads(json_str)
                if "arguments" in action_data:
                    result["action"] = action_data["arguments"]
                else:
                    result["action"] = action_data
                return result
            except json.JSONDecodeError:
                pass  # Try next pattern

        # Pattern 3: Raw JSON object (starts with { and ends with })
        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            thought = response[:json_match.start()].strip()
            result["thought"] = thought

            try:
                action_data = json.loads(json_str)
                if "arguments" in action_data:
                    result["action"] = action_data["arguments"]
                else:
                    result["action"] = action_data
                return result
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse raw JSON: {e}")

        # Pattern 4: Try to find JSON-like structure starting with "type" key
        # This handles cases like: \n  "type": "click", ...
        json_match = re.search(r'"type"\s*:\s*"[^"]+"\s*[,}]', response)
        if json_match:
            # Try to find the full JSON object around this
            start = response.rfind('{', 0, json_match.start())
            if start != -1:
                # Find matching closing brace
                depth = 0
                end = start
                for i, c in enumerate(response[start:], start):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                json_str = response[start:end]
                thought = response[:start].strip()
                result["thought"] = thought

                try:
                    action_data = json.loads(json_str)
                    if "arguments" in action_data:
                        result["action"] = action_data["arguments"]
                    else:
                        result["action"] = action_data
                    return result
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse type-based JSON: {e}")

        # Pattern 5: Handle malformed JSON like "action: 'left_click', 'coordinate': [x, y]"
        # Missing opening brace, single quotes
        action_match = re.search(r'action:\s*[\'"]([^"\']+)[\'"]', response, re.IGNORECASE)
        if action_match:
            action_type = action_match.group(1)
            thought = response[:action_match.start()].strip()
            result["thought"] = thought
            
            # Try to extract coordinate if present
            coord_match = re.search(r'coordinate[\'"]?\s*:\s*\[(\d+),\s*(\d+)\]', response)
            if coord_match:
                x, y = int(coord_match.group(1)), int(coord_match.group(2))
                result["action"] = {"action": action_type, "coordinate": [x, y]}
                self.logger.debug(f"Parsed malformed action: {result['action']}")
                return result
            
            # Check for text parameter
            text_match = re.search(r'text[\'"]?\s*:\s*[\'"]([^"\']+)[\'"]', response)
            if text_match:
                text = text_match.group(1)
                result["action"] = {"action": action_type, "text": text}
                self.logger.debug(f"Parsed malformed action with text: {result['action']}")
                return result
            
            # Just the action type
            result["action"] = {"action": action_type}
            self.logger.debug(f"Parsed malformed action (type only): {result['action']}")
            return result

        # No valid JSON found
        result["thought"] = response.strip()
        self.logger.warning(f"No action JSON found in response: {response[:200]}...")
        result["action"] = {"error": "No valid action JSON found in response"}

        return result

    def reset_session(self) -> None:
        """Reset the action history and memorized facts for a new task."""
        self._action_history = []
        self._memorized_facts = []
        self.logger.info("Fara session reset")

    def get_action_history(self) -> List[Dict[str, Any]]:
        """Get the history of actions taken in the current session."""
        return self._action_history.copy()

    def get_memorized_facts(self) -> List[str]:
        """Get the list of facts memorized during the session."""
        return self._memorized_facts.copy()

    def is_task_complete(self) -> bool:
        """Check if the last action was a termination."""
        if not self._action_history:
            return False
        last_action = self._action_history[-1].get("action", {})
        return last_action.get("action") == "terminate"

    def get_task_status(self) -> Optional[str]:
        """Get the task completion status if terminated."""
        if not self.is_task_complete():
            return None
        last_action = self._action_history[-1].get("action", {})
        return last_action.get("status")

    def _do_generate(
        self,
        prompt: str = "",
        action: LLMActionType = LLMActionType.CHAT,
        system_prompt: Optional[str] = None,
        rag_system_prompt: Optional[str] = None,
        llm_request: Optional[LLMRequest] = None,
        do_tts_reply: bool = True,
        image_data: Optional[Union[str, bytes]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a response using Fara for computer use tasks.

        For non-computer-use tasks, this delegates to the standard LLM.
        For computer use, it uses the get_next_action method.
        """
        if image_data:
            # This is a computer use request with a screenshot
            result = self.get_next_action(
                screenshot=image_data,
                goal=prompt,
            )
            return {
                "response": result.get("thought", ""),
                "action": result.get("action", {}),
                "raw": result,
            }
        else:
            # No screenshot - delegate to parent for regular text generation
            return super()._do_generate(
                prompt=prompt,
                action=action,
                system_prompt=system_prompt,
                rag_system_prompt=rag_system_prompt,
                llm_request=llm_request,
                do_tts_reply=do_tts_reply,
                **kwargs,
            )
