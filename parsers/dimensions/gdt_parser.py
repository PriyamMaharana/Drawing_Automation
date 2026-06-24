import logging

logger = logging.getLogger(__name__)

class GDTParser:
    @staticmethod
    def parse_composite(gdt_string: str) -> dict:
        """
        Layer 6.2: Parses composite/stacked GD&T frames into parent-child relationships.
        Example: '⌖ | 0.03 | A | B \n ⌯ | 0.5 | C | D'
        """
        if not gdt_string:
            return {}

        frames = gdt_string.strip().split('\n')
        parsed_frames = []
        
        for frame in frames:
            parts = [p.strip() for p in frame.split('|')]
            if len(parts) >= 2:
                parsed_frame = {
                    "characteristic": parts[0],
                    "tolerance": parts[1],
                    "datums": parts[2:] if len(parts) > 2 else []
                }
                parsed_frames.append(parsed_frame)
                
        return {
            "type": "Feature Control Frame", 
            "frames": parsed_frames
        }
        