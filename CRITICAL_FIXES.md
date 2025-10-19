# Critical Fixes Needed

## Issue 1: Knowledge Extraction Failing

**Problem:** `user_facts.json` is empty even after conversation about back pain.

**Root Cause:** The correction detection feature may be causing extraction to fail silently if there's an error.

**Fix:** Add better error handling and logging in correction detection.

## Issue 2: No Conversation Memory

**Problem:** Bot asking same question 3 times, not reading previous responses:
```
User: "yes i keep stretching but it only helps a bit"
Bot: "Have you tried any specific exercises or stretches?"
User: "i just said that i have tried stretches"
Bot: "Have you tried any specific exercises or stretches?"
```

**Root Cause:** `chat_history=[]` in REACT agent tool - conversation history not being passed.

**Analysis:**
- Logs show: `REACT AGENT TOOL {'input': '...', 'chat_history': [], 'tool_choice': '...'}`
- Empty chat_history means agent has no context
- Each response is independent, no memory of previous exchanges

**Fix Needed:**
1. Verify `chat_memory` is being populated correctly
2. Ensure `chat_memory.get()` returns recent conversation
3. Check that conversation messages are being added to memory after each exchange

## Issue 3: Low Temperature Causing Repetition

**Problem:** Identical responses ("Have you tried any specific exercises or stretches?" repeated 3 times)

**Current Settings:**
- Extraction temperature: 0.1 (too low, causes repetition)
- Chat temperature: Likely also too low

**Fix:** Increase temperature to 0.7-0.8 for more varied responses.

## Recommended Fixes

### 1. Fix Correction Detection Error Handling

File: `user_knowledge_manager.py`

Make `_detect_corrections()` fail gracefully:
```python
def _detect_corrections(self, user_message: str, llm_callable) -> Optional[List[Dict]]:
    try:
        # ... existing code ...
    except Exception as e:
        self.logger.warning(f"Correction detection failed: {e}")
        return None  # Don't block fact extraction if corrections fail
```

### 2. Debug Chat Memory

Add logging to see if chat_memory is populated:
```python
# In react_agent_tool.py, line ~125
chat_history = (
    (self.agent.chat_memory.get() if self.agent.chat_memory else [])
    ...
)
print(f"DEBUG: chat_memory exists: {self.agent.chat_memory is not None}")
print(f"DEBUG: chat_history length: {len(chat_history)}")
```

### 3. Increase Temperature

In `llm_settings.py`:
```python
temperature: float = 0.7  # Current: 0.1 (too low)
```

### 4. Add Recent Messages to System Prompt

In `prompt_builder.py`, add conversation context:
```python
def _build(...):
    ...
    # Add recent conversation context
    if self.agent.chat_memory:
        recent = self.agent.chat_memory.get()[-5:]  # Last 5 messages
        if recent:
            prompt_parts.append("\n## Recent Conversation:")
            for msg in recent:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                prompt_parts.append(f"{role}: {content}")
    ...
```

## Investigation Steps

1. **Check if chat_memory is None:**
   ```python
   print(f"Agent chat_memory: {self.agent.chat_memory}")
   print(f"Chat_memory type: {type(self.agent.chat_memory)}")
   ```

2. **Check if messages are being added:**
   Look for calls to `chat_memory.put()` or `chat_memory.add()`

3. **Check conversation_id:**
   Empty chat_history might indicate conversation_id mismatch

4. **Test extraction directly:**
   ```python
   from airunner.components.knowledge.user_knowledge_manager import UserKnowledgeManager
   km = UserKnowledgeManager()
   
   # Simulate extraction
   def mock_llm(prompt, **kwargs):
       return '[{"text": "User has back pain", "category": "health", "confidence": 0.9}]'
   
   facts = km.extract_facts_from_text(
       "my back hurts", 
       "I'm sorry to hear that",
       mock_llm
   )
   print(f"Extracted: {facts}")
   ```

## Priority

1. **HIGH**: Fix chat_memory/chat_history (conversation quality)
2. **HIGH**: Fix knowledge extraction (core feature broken)
3. **MEDIUM**: Increase temperature (quality improvement)
4. **LOW**: Add conversation context to system prompt (nice-to-have)
