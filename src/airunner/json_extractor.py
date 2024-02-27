import json
import re


class JSONExtractor(json.JSONDecoder):
    def decode(self, s):
        self.json_objects = []
        # Remove trailing characters
        while s:
            try:
                # Try to decode the string as JSON
                obj, end = super().raw_decode(s)
                self.json_objects.append(obj)
                s = s[end:].lstrip()
            except json.JSONDecodeError:
                # If the string is not valid JSON, find the first valid JSON object
                match = re.match(r'[^\{]+(\{[^\}]+\}).*', s)
                if match:
                    json_part = match.group(1)  # Extract the JSON object from the match
                    s = s[match.end():]
                    s = s.replace("```json", "").replace("```", "")
                    try:
                        # Try to decode the extracted part as JSON
                        obj = json.loads(json_part)
                        self.json_objects.append(obj)
                    except json.JSONDecodeError:
                        # If the extracted part is not valid JSON, ignore it
                        pass
                else:
                    break
        return self.json_objects

    def raw_decode(self, s, idx=0):
        obj, end = super().raw_decode(s, idx)
        self.json_objects.append(obj)
        return obj, end
