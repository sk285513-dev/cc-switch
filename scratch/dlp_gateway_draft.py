import re
from functools import wraps
from typing import Callable, Any

class DLPGateway:
    """
    A lightweight Data Loss Prevention (DLP) Gateway for intercepting and redacting
    sensitive personal information such as Taiwan ID numbers and Mobile phone numbers.
    """
    # Regex for Taiwan ID: uppercase letter, '1' or '2', followed by 8 digits
    ID_PATTERN = re.compile(r'[A-Z][12]\d{8}')
    
    # Regex for Mobile: 09 followed by 8 digits, with optional hyphens
    MOBILE_PATTERN = re.compile(r'09\d{2}-?\d{3}-?\d{3}')

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Redact sensitive information from the given text.
        """
        if not isinstance(text, str):
            return text
            
        redacted_text = cls.ID_PATTERN.sub('[REDACTED]', text)
        redacted_text = cls.MOBILE_PATTERN.sub('[REDACTED]', redacted_text)
        
        return redacted_text

def dlp_intercept(func: Callable) -> Callable:
    """
    API Interceptor decorator.
    Intercepts payloads (arguments) passed to the function and redacts
    sensitive information before the function processes them.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Sanitize positional arguments (only strings)
        sanitized_args = tuple(
            DLPGateway.sanitize_text(arg) if isinstance(arg, str) else arg 
            for arg in args
        )
        
        # Sanitize keyword arguments (only strings)
        sanitized_kwargs = {
            k: DLPGateway.sanitize_text(v) if isinstance(v, str) else v 
            for k, v in kwargs.items()
        }
        
        return func(*sanitized_args, **sanitized_kwargs)
    return wrapper
