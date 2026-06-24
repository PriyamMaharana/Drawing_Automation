import re
import logging

logger = logging.getLogger(__name__)

class ManufacturingDataNormalizer:
    @staticmethod
    def normalize(raw_string: str) -> dict:
        """
        Layer 6.5: Converts engineering strings into explicit limits and types.
        Handles standard math, Surface Finishes (N9), Multipliers (4X), Min/Max, and Standalone Tolerances.
        """
        raw_string = raw_string.strip()
        result = {
            "nominal": None,
            "upper_limit": None,
            "lower_limit": None,
            "type": "Unknown",
            "is_reference": False,
            "raw_value": raw_string 
        }

        if not raw_string:
            return result

        # 1. Reference Dimension Check
        if raw_string.startswith('(') and raw_string.endswith(')'):
            result['is_reference'] = True
            raw_string = raw_string[1:-1].strip()

        # 2. Surface Finish Check
        if re.match(r'^(N\d{1,2}|Ra\s*\d+(?:\.\d+)?)$', raw_string, re.IGNORECASE):
            result['type'] = "Surface Finish"
            result['nominal'] = raw_string
            return result

        # 3. GD&T and Datums
        gdt_symbols = ['⌖', '⊥', '⟂', '//', '∥', '∠', '◎', '↗', '⌰', '⌭', '⌯', '▱', '⌓']
        if any(sym in raw_string for sym in gdt_symbols) or '|' in raw_string:
            result['type'] = "Feature Control Frame"
            return result
            
        elif re.match(r'^\[?[A-Z]{1,2}\]?$', raw_string):
            result['type'] = "Datum"
            result['nominal'] = raw_string.strip('[]')
            return result

        # 4. Standalone Tolerance Check (e.g. "±0.5" without a base value)
        if raw_string.startswith('±'):
            result['type'] = "Tolerance Only"
            tol_match = re.search(r'±\s*(\d+(?:\.\d+)?)', raw_string)
            if tol_match:
                tol = float(tol_match.group(1))
                result['upper_limit'] = f"+{tol}"
                result['lower_limit'] = f"-{tol}"
            return result

        # 5. Min / Max detection
        is_min = bool(re.search(r'\bMIN\.?\b', raw_string, re.IGNORECASE))
        is_max = bool(re.search(r'\bMAX\.?\b', raw_string, re.IGNORECASE))

        # 6. Angular / Chamfer (Strict check to prevent catching 'X4' quantities)
        # Only triggers if ° is present OR it strictly matches Num x Num without Ø
        if '°' in raw_string or (re.search(r'\d+(?:\.\d+)?\s*[xX]\s*\d+(?:\.\d+)?(?!.*[A-Za-z])', raw_string) and 'Ø' not in raw_string and '⌀' not in raw_string):
            result['type'] = "Angular / Chamfer"
            result['nominal'] = raw_string 
            return result

        # 7. Isolate Base Type
        if 'Ø' in raw_string or '⌀' in raw_string:
            result['type'] = "Diameter"
        elif 'R' in raw_string:
            result['type'] = "Radius"
        else:
            result['type'] = "Linear"

        # 8. Quantity Multiplier Clean-up (Removes "4X " or " X4" so it doesn't break math)
        clean_math_string = re.sub(r'^\d+\s*[xX]\s+', '', raw_string)
        clean_math_string = re.sub(r'\s*[xX]\s*\d+$', '', clean_math_string)

        # 9. Extract Nominal Base Value 
        # (Prevents catching numbers inside quotes like "L ± 5")
        if '"' in clean_math_string or re.search(r'^[A-Za-z]\s*±', clean_math_string):
            result['type'] = "Variable Dimension"
            result['nominal'] = clean_math_string
            return result

        nominal_match = re.search(r'[Ø⌀R]?\s*(\d+(?:\.\d+)?)', clean_math_string)
        if nominal_match:
            result['nominal'] = float(nominal_match.group(1))
            result['upper_limit'] = result['nominal']
            result['lower_limit'] = result['nominal']
        else:
            return result

        # 10. Extract Tolerances and Calculate Limits
        if '±' in clean_math_string:
            tol_match = re.search(r'±\s*(\d+(?:\.\d+)?)', clean_math_string)
            if tol_match:
                tol = float(tol_match.group(1))
                result['upper_limit'] = round(result['nominal'] + tol, 4)
                result['lower_limit'] = round(result['nominal'] - tol, 4)
                
        elif '+' in clean_math_string and '-' in clean_math_string:
            plus_match = re.search(r'\+\s*(\d+(?:\.\d+)?)', clean_math_string)
            minus_match = re.search(r'-\s*(\d+(?:\.\d+)?)', clean_math_string)
            if plus_match and minus_match:
                result['upper_limit'] = round(result['nominal'] + float(plus_match.group(1)), 4)
                result['lower_limit'] = round(result['nominal'] - float(minus_match.group(1)), 4)
                
        elif '+' in clean_math_string: # Unilateral Positive
            plus_match = re.search(r'\+\s*(\d+(?:\.\d+)?)', clean_math_string)
            if plus_match:
                result['upper_limit'] = round(result['nominal'] + float(plus_match.group(1)), 4)
                
        elif '-' in clean_math_string: # Unilateral Negative
            minus_match = re.search(r'-\s*(\d+(?:\.\d+)?)', clean_math_string)
            if minus_match:
                result['lower_limit'] = round(result['nominal'] - float(minus_match.group(1)), 4)

        # 11. Apply MIN / MAX Constraint Overrides
        if is_min:
            result['upper_limit'] = "Infinity" # Open upper bound
            result['type'] = f"{result['type']} (Min)"
        elif is_max:
            result['lower_limit'] = 0.0 # Bounded by zero
            result['type'] = f"{result['type']} (Max)"

        return result