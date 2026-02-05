import re

class VietglishProcessor:
    def __init__(self):
        # Common Viet-glish patterns
        self.patterns = [
            {"name": "According to... showed that", "pattern": r"According to .* showed that", "type": "redundancy"},
            {"name": "Present perfect confusion", "pattern": r"has been .* since \d+", "type": "tense"},
            # Add more patterns here
        ]
    
    def analyze(self, text: str) -> list:
        errors = []
        for p in self.patterns:
            if re.search(p["pattern"], text, re.IGNORECASE):
                errors.append({
                    "pattern": p["name"],
                    "type": p["type"],
                    "found": True
                })
        return errors

vietglish_processor = VietglishProcessor()
