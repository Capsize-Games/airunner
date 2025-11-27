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
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.enums import LLMActionType, ModelType, ModelStatus


# Default Fara model path
DEFAULT_FARA_MODEL = "microsoft/Fara-7B"

# Fara's system prompt with computer use function signature
# Extended to support both web and general desktop automation
FARA_SYSTEM_PROMPT = """You are a computer automation agent that performs actions on a desktop computer to fulfill user requests by calling various tools.

You can interact with:
- Web browsers (navigate, search, fill forms, click links)
- Desktop applications (open apps, interact with windows, menus)
- Files and folders (through GUI interactions)
- Any graphical interface visible on screen

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

{
  "type": "function",
  "function": {
    "name": "computer_use",
    "description": "Use a mouse and keyboard to interact with a computer, and take screenshots.\\n* This is an interface to a desktop GUI. You can interact with any visible application.\\n* Click on desktop icons or taskbar to start applications.\\n* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions.\\n* The screen's resolution is {screen_width}x{screen_height}.\\n* Whenever you intend to move the cursor to click on an element, consult the screenshot to determine the coordinates.\\n* If clicking on an element fails, try adjusting your cursor position.",
    "parameters": {
      "properties": {
        "action": {
          "description": "The action to perform. The available actions are:\\n* key: Performs key down presses on the arguments passed in order, then performs key releases in reverse order. Includes 'Enter', 'Alt', 'Shift', 'Tab', 'Control', 'Backspace', 'Delete', 'Escape', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'PageDown', 'PageUp', etc.\\n* type: Type a string of text on the keyboard.\\n* mouse_move: Move the cursor to a specified (x, y) pixel coordinate on the screen.\\n* left_click: Click the left mouse button.\\n* right_click: Click the right mouse button (for context menus).\\n* double_click: Double-click the left mouse button (for opening files/folders).\\n* drag: Drag from one coordinate to another.\\n* scroll: Performs a scroll of the mouse scroll wheel.\\n* hotkey: Execute a keyboard shortcut (e.g., Ctrl+S, Alt+Tab).\\n* open_application: Open an application by name.\\n* visit_url: Visit a specified URL in browser.\\n* web_search: Perform a web search with a specified query.\\n* history_back: Go back to the previous page in the browser history.\\n* pause_and_memorize_fact: Remember an important fact for later use.\\n* wait: Wait for a specified amount of time.\\n* terminate: End the task with success or failure status.",
          "enum": ["key", "type", "mouse_move", "left_click", "right_click", "double_click", "drag", "scroll", "hotkey", "open_application", "visit_url", "web_search", "history_back", "pause_and_memorize_fact", "wait", "terminate"],
          "type": "string"
        },
        "keys": {"description": "Required by action=key and action=hotkey. Array of key names.", "type": "array"},
        "text": {"description": "Required only by action=type.", "type": "string"},
        "coordinate": {"description": "(x, y) coordinates for mouse actions. Required by action=left_click, action=right_click, action=double_click, action=mouse_move, and action=type.", "type": "array"},
        "start_coordinate": {"description": "Starting (x, y) coordinates. Required only by action=drag.", "type": "array"},
        "end_coordinate": {"description": "Ending (x, y) coordinates. Required only by action=drag.", "type": "array"},
        "pixels": {"description": "Amount of scrolling. Positive = up, Negative = down. Required only by action=scroll.", "type": "number"},
        "url": {"description": "The URL to visit. Required only by action=visit_url.", "type": "string"},
        "query": {"description": "The query to search for. Required only by action=web_search.", "type": "string"},
        "application": {"description": "Application name to open. Required only by action=open_application.", "type": "string"},
        "fact": {"description": "The fact to remember for the future. Required only by action=pause_and_memorize_fact.", "type": "string"},
        "time": {"description": "Seconds to wait. Required only by action=wait.", "type": "number"},
        "status": {"description": "Status of the task. Required only by action=terminate.", "type": "string", "enum": ["success", "failure"]}
      },
      "required": ["action"],
      "type": "object"
    }
  }
}

For each function call, return a JSON object with the function name and arguments within XML tags:

```json
{
  "name": "<function-name>",
  "arguments": <args-json-object>
}
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
    _screen_width: int = 1428
    _screen_height: int = 896
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
            str: Path to the model directory or HuggingFace model ID
        """
        model_version = getattr(self, '_fara_model_path', None)
        if not model_version:
            model_version = DEFAULT_FARA_MODEL

        # Check if it's a local path
        if os.path.exists(os.path.expanduser(model_version)):
            return os.path.expanduser(model_version)

        return model_version

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

    def _get_quantization_config(self) -> Optional[BitsAndBytesConfig]:
        """Get 4-bit quantization config for memory efficiency."""
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    def _load_tokenizer(self) -> None:
        """
        Load the AutoProcessor for Qwen2.5-VL based Fara model.

        The processor handles both text and image inputs.
        """
        if self._processor is not None:
            return

        self.logger.debug(f"Loading Fara processor from {self.model_path}")
        try:
            self._processor = AutoProcessor.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=True,
            )
            self._tokenizer = self._processor  # For compatibility
            self.logger.debug("Fara processor loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading Fara processor: {e}")
            self._processor = None
            self._tokenizer = None

    def _load_model(self) -> None:
        """
        Load the Fara-7B model with optional quantization.
        """
        if self._model is not None:
            return

        self.logger.debug(f"Loading Fara model from {self.model_path}")
        try:
            # Use 4-bit quantization by default for 16GB GPUs
            quantization_config = self._get_quantization_config()

            self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                quantization_config=quantization_config,
            ).eval()
            self.logger.info("Fara-7B model loaded successfully (4-bit quantized)")
        except Exception as e:
            self.logger.error(f"Error loading Fara model: {e}")
            self._model = None

    def _prepare_image(self, image: Union[str, bytes, Image.Image]) -> Image.Image:
        """
        Convert various image formats to PIL Image.

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
        """Build the system prompt with current screen resolution."""
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

        # Build user message
        user_content = f"Goal: {goal}\n"
        if facts_text:
            user_content += f"\n{facts_text}\n"
        if history_text:
            user_content += f"\nPrevious actions:\n{history_text}\n"
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

        # Process inputs
        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(
            text=[text],
            images=[image],
            return_tensors="pt",
            padding=True,
        ).to(self._model.device)

        # Generate response
        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=True,
                temperature=0.1,
                top_p=0.9,
            )

        # Decode response
        response = self._processor.batch_decode(
            outputs[:, inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )[0]

        # Parse the response
        result = self._parse_response(response)

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

        # Extract thought (text before JSON block)
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
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse action JSON: {e}")
                result["action"] = {"error": "Failed to parse action"}
        else:
            # No JSON block found, might be just thought
            result["thought"] = response.strip()
            self.logger.warning("No action JSON found in response")

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
