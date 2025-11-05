import torch
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm
from typing import Dict, Any

# Mock objects for demonstration if transformers is not installed.
# In a real scenario, you would import these from the transformers library.
try:
    from transformers import PreTrainedModel, PreTrainedTokenizer
except ImportError:
    print(
        "Warning: `transformers` library not found. Using mock objects for demonstration."
    )

    # Define placeholder classes to allow the code to be parsed and understood
    class PreTrainedModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.layer_norm = nn.LayerNorm(128)
            self.linear = nn.Linear(128, 128)

        def forward(self, input_ids, **kwargs):
            return torch.randn(
                1, input_ids.shape[1], 50257
            )  # Mock output logits

    class PreTrainedTokenizer:
        def __call__(self, text, return_tensors=None):
            return {"input_ids": torch.randint(0, 50257, (1, 10))}

        def batch_decode(self, tokens):
            return ["mock output"]

        def pad_token_id(self):
            return 0


class MEMOIR:
    """
    Implementation of the MEMOIR framework for lifelong model editing.

    This class wraps a pre-trained transformer model and applies the MEMOIR
    algorithm to edit its knowledge base without full retraining. It introduces
    a residual memory module and uses a TopHash mechanism to localize edits,
    minimizing catastrophic forgetting.

    Args:
        model (PreTrainedModel): The pre-trained transformer model to be edited.
        tokenizer (PreTrainedTokenizer): The tokenizer associated with the model.
        layer_path (str): The path to the layer to be edited (e.g., 'model.layers.27.mlp.down_proj').
        k (int): The number of active indices for the TopHash mask.
        tau (float): The threshold for conditional knowledge activation during inference.
        lr (float): Learning rate for the SGD optimizer during editing.
        edit_steps (int): The number of optimization steps for each edit.
        device (str): The device to run the model on ('cuda' or 'cpu').
    """

    def __init__(
        self,
        model: PreTrainedModel,
        tokenizer: PreTrainedTokenizer,
        layer_path: str,
        k: int = 4096,
        tau: float = 0.6,
        lr: float = 1.0,
        edit_steps: int = 30,
        device: str = "cpu",
    ):

        self.model = model.to(device)
        self.tokenizer = tokenizer
        self.layer_path = layer_path
        self.k = k
        self.tau = tau
        self.lr = lr
        self.edit_steps = edit_steps
        self.device = device

        # --- Locate the target layer and its parent module ---
        path_parts = layer_path.split(".")
        parent_module = self.model
        for part in path_parts[:-1]:
            parent_module = getattr(parent_module, part)
        self.target_layer_name = path_parts[-1]
        self.target_layer = getattr(parent_module, self.target_layer_name)

        if not isinstance(self.target_layer, nn.Linear):
            raise TypeError(
                f"Target layer {layer_path} must be a torch.nn.Linear module."
            )

        # --- Initialize MEMOIR components ---
        self.d_in = self.target_layer.in_features
        self.d_out = self.target_layer.out_features

        # W_0 is the original pre-trained weight matrix
        self.W_0 = self.target_layer.weight.data.clone().to(self.device)

        # W_m is the residual memory, initialized to zeros
        self.W_m = torch.zeros_like(self.W_0).to(self.device)
        self.W_m.requires_grad = True  # Make it trainable

        # Edit database to store TopHash masks
        self.edit_masks: Dict[int, torch.Tensor] = {}
        self.edit_id_counter = 0

        # Fixed permutation for TopHash
        self.permutation = torch.randperm(self.d_in).to(self.device)

        # Optimizer for the residual memory
        self.optimizer = optim.SGD([self.W_m], lr=self.lr)

        # Register forward hook to intercept layer activations
        self.hook_handle = self.target_layer.register_forward_hook(
            self._forward_hook
        )

        # Variables to store intermediate values during forward pass
        self._hook_storage: Dict[str, Any] = {}

    def _tophash(self, activations: torch.Tensor) -> torch.Tensor:
        """
        Computes the TopHash mask for a given set of activations.

        Args:
            activations (torch.Tensor): The input activations to the target layer.
                                        Shape: (batch_size, seq_len, d_in)

        Returns:
            torch.Tensor: A binary mask of shape (d_in,).
        """
        # Use activations of the last token as the most informative summary
        last_token_activations = activations[0, -1, :]

        # 1. Top-k selection based on magnitude
        top_k_vals, _ = torch.topk(last_token_activations.abs(), self.k)
        threshold = top_k_vals[-1]
        top_k_mask = (last_token_activations.abs() >= threshold).float()

        # 2. Apply fixed permutation
        permuted_mask = top_k_mask[self.permutation]

        return permuted_mask

    def _get_activations(self, prompt: str) -> torch.Tensor:
        """
        Gets the input activations to the target layer for a given prompt.
        This is achieved by running a forward pass and capturing the activations
        via a pre-forward hook on the target layer's parent module.
        """
        activations = None

        # We need a hook to capture the *input* to our target linear layer
        def capture_activations_hook(module, input, output):
            nonlocal activations
            activations = input[0].detach()

        hook = self.target_layer.register_forward_pre_hook(
            capture_activations_hook
        )

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(
                self.device
            )
            self.model(**inputs)  # Run a forward pass to trigger the hook
        finally:
            hook.remove()  # Always remove the hook

        if activations is None:
            raise RuntimeError("Failed to capture activations.")

        return activations

    def _forward_hook(
        self, module: nn.Module, args: tuple, output: torch.Tensor
    ) -> torch.Tensor:
        """
        The forward hook that applies the MEMOIR logic at inference time.
        This function replaces the original output of the target layer.
        """
        # The input activations to the layer
        activations = args[0]

        # Original layer output
        original_output = activations @ self.W_0.t()

        # Check if we are in inference mode with a mask provided
        if "inference_mask" in self._hook_storage:
            inference_mask = self._hook_storage["inference_mask"]

            # If the mask is not None, it means we found a relevant edit
            if inference_mask is not None:
                # Masked activations for the residual memory
                masked_activations = activations * inference_mask
                # Residual output
                residual_output = masked_activations @ self.W_m.t()
                return original_output + residual_output

        return original_output

    def edit(self, edit_prompt: str, target_output: str):
        """
        Edits the model's knowledge using the given prompt and target.

        Args:
            edit_prompt (str): The prompt that needs a new fact (e.g., "The capital of France is").
            target_output (str): The correct output for the prompt (e.g., "Paris").
        """
        self.model.train()  # Set to training mode for gradients

        # 1. Get activations and compute the edit mask
        activations = self._get_activations(edit_prompt)
        edit_mask = self._tophash(activations)

        # Store the mask in the database
        self.edit_masks[self.edit_id_counter] = edit_mask
        self.edit_id_counter += 1

        # 2. Fine-tune the residual memory W_m
        target_ids = self.tokenizer(target_output, return_tensors="pt").to(
            self.device
        )["input_ids"]

        # We set the inference_mask to our new edit_mask to ensure the forward pass uses it
        self._hook_storage["inference_mask"] = edit_mask

        # Optimization loop
        pbar = tqdm(
            range(self.edit_steps), desc=f"Editing for '{edit_prompt[:50]}...'"
        )
        for step in pbar:
            self.optimizer.zero_grad()

            # Get model output
            inputs = self.tokenizer(edit_prompt, return_tensors="pt").to(
                self.device
            )
            outputs = self.model(**inputs)
            logits = (
                outputs
                if isinstance(outputs, torch.Tensor)
                else outputs.logits
            )

            # Calculate loss only on the target tokens
            shift_logits = logits[..., -target_ids.size(1) :, :].contiguous()
            loss = nn.CrossEntropyLoss()(
                shift_logits.view(-1, shift_logits.size(-1)),
                target_ids.view(-1),
            )

            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

            # Backpropagate
            loss.backward()

            # The gradients for W_m will naturally be sparse due to the hook logic.
            # We can now step the optimizer.
            self.optimizer.step()

        # Clean up storage
        del self._hook_storage["inference_mask"]

    def __call__(self, prompt: str, max_new_tokens: int = 20) -> str:
        """
        Generates a response from the edited model.

        Args:
            prompt (str): The input prompt for the model.
            max_new_tokens (int): The maximum number of tokens to generate.

        Returns:
            str: The generated text.
        """
        self.model.eval()

        with torch.no_grad():
            # 1. Get activations and compute the query mask
            query_activations = self._get_activations(prompt)
            query_mask = self._tophash(query_activations)

            # 2. Find the best matching edit mask from the database
            best_match_id = -1
            max_overlap = -1

            for edit_id, edit_mask in self.edit_masks.items():
                overlap = (query_mask * edit_mask).sum()
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_match_id = edit_id

            # 3. Conditional knowledge activation
            matched_mask = None
            if best_match_id != -1:
                overlap_ratio = max_overlap / self.k
                if overlap_ratio >= self.tau:
                    matched_mask = self.edit_masks[best_match_id]

            # Store the matched mask for the forward hook to use
            self._hook_storage["inference_mask"] = matched_mask

            # 4. Generate the output
            inputs = self.tokenizer(prompt, return_tensors="pt").to(
                self.device
            )

            # Use model's generate method if available, otherwise just do a forward pass
            if hasattr(self.model, "generate"):
                output_tokens = self.model.generate(
                    **inputs, max_new_tokens=max_new_tokens
                )
                result = self.tokenizer.batch_decode(output_tokens)[0]
            else:
                # Fallback for mock/simple models
                outputs = self.model(**inputs)
                output_tokens = torch.argmax(outputs.logits, dim=-1)
                result = self.tokenizer.batch_decode(output_tokens)[0]

            # Clean up the storage
            del self._hook_storage["inference_mask"]

        return result

    def detach(self):
        """Removes the forward hook, restoring the model to its original state."""
        if self.hook_handle:
            self.hook_handle.remove()


if __name__ == "__main__":
    # --- Example Usage ---
    # This example uses mock objects. To use a real model, you would load it from
    # the Hugging Face Hub.

    print("--- Initializing Mock Model and Tokenizer ---")
    mock_model = PreTrainedModel()
    mock_tokenizer = PreTrainedTokenizer()

    # In a real scenario, you would do:
    # from transformers import AutoModelForCausalLM, AutoTokenizer
    # model_name = "gpt2"
    # real_model = AutoModelForCausalLM.from_pretrained(model_name)
    # real_tokenizer = AutoTokenizer.from_pretrained(model_name)

    print("--- Setting up MEMOIR ---")
    # Let's pretend we want to edit layer 27 of a LLaMA-like model.
    # For our mock model, we'll just edit the 'linear' layer.
    memoir_editor = MEMOIR(
        model=mock_model,
        tokenizer=mock_tokenizer,
        layer_path="linear",  # Path to the layer in our mock model
        k=512,  # Smaller k for mock model's smaller dimension
        tau=0.5,
        edit_steps=10,
    )

    print("\n--- Generating before edit ---")
    prompt_before = "The inventor of the light bulb was"
    output_before = memoir_editor(prompt_before)
    print(f"Prompt: {prompt_before}")
    print(f"Output: {output_before}")

    print("\n--- Performing an edit ---")
    edit_prompt = "The inventor of the light bulb was"
    target_output = "Thomas Edison"
    memoir_editor.edit(edit_prompt, target_output)

    print("\n--- Generating after edit ---")
    prompt_after = "Who invented the light bulb?"  # A rephrased query
    output_after = memoir_editor(prompt_after)
    print(f"Prompt: {prompt_after}")
    print(f"Output (should be related to Thomas Edison): {output_after}")

    print("\n--- Testing unrelated prompt for locality ---")
    unrelated_prompt = "The capital of France is"
    unrelated_output = memoir_editor(unrelated_prompt)
    print(f"Prompt: {unrelated_prompt}")
    print(f"Output (should be original behavior): {unrelated_output}")

    # Detach the hook to restore original model behavior
    memoir_editor.detach()
    print("\n--- MEMOIR hook detached. Model restored to original state. ---")
