"""Built-in functions for expression evaluation."""

from datetime import datetime, timedelta
from typing import Any


class BuiltinFunctions:
    """Built-in functions available in rule expressions."""

    @staticmethod
    def NOW() -> str:
        """Get the current datetime as a formatted string.

        Returns:
            Current datetime as "yyyy-mm-dd HH:MM:SS"
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def CONCAT(*args: Any) -> str:
        """Concatenate values into a string.

        Args:
            *args: Values to concatenate

        Returns:
            Concatenated string
        """
        return "".join(str(a) for a in args)

    @staticmethod
    def TODAY() -> str:
        """Get the current date as a formatted string (time set to midnight).

        Returns:
            Current date as "yyyy-mm-dd 00:00:00"
        """
        return datetime.now().strftime("%Y-%m-%d 00:00:00")

    @staticmethod
    def DATETIME_ADD(dt: Any, amount: int, unit: str = "days") -> str:
        """Add a time interval to a datetime.

        Args:
            dt: Base datetime (object or string)
            amount: Amount to add (can be negative)
            unit: Time unit - "days", "hours", "minutes", "seconds"

        Returns:
            New datetime string with interval added
        """
        if isinstance(dt, str):
            try:
                dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Handle YYYY-MM-DD
                dt = datetime.strptime(dt, "%Y-%m-%d")

        if unit == "days":
            res = dt + timedelta(days=amount)
        elif unit == "hours":
            res = dt + timedelta(hours=amount)
        elif unit == "minutes":
            res = dt + timedelta(minutes=amount)
        elif unit == "seconds":
            res = dt + timedelta(seconds=amount)
        else:
            raise ValueError(f"Unknown time unit: {unit}")

        return res.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def DATETIME_DIFF(dt1: Any, dt2: Any, unit: str = "seconds") -> int:
        """Calculate the difference between two datetimes.

        Args:
            dt1: First datetime (object or string)
            dt2: Second datetime (object or string)
            unit: Time unit - "days", "hours", "minutes", "seconds"

        Returns:
            Difference as integer in specified unit
        """

        def to_dt(val):
            if isinstance(val, str):
                try:
                    return datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return datetime.strptime(val, "%Y-%m-%d")
            return val

        d1 = to_dt(dt1)
        d2 = to_dt(dt2)
        diff = d1 - d2
        total_seconds = diff.total_seconds()

        if unit == "days":
            return int(total_seconds / 86400)
        elif unit == "hours":
            return int(total_seconds / 3600)
        elif unit == "minutes":
            return int(total_seconds / 60)
        elif unit == "seconds":
            return int(total_seconds)
        else:
            raise ValueError(f"Unknown time unit: {unit}")

    @staticmethod
    def LENGTH(value: str | list | dict) -> int:
        """Get the length of a string, list, or dict.

        Args:
            value: Value to measure

        Returns:
            Length of the value
        """
        return len(value)

    @staticmethod
    def UPPER(value: str) -> str:
        """Convert a string to uppercase.

        Args:
            value: String to convert

        Returns:
            Uppercase string
        """
        return str(value).upper()

    @staticmethod
    def LOWER(value: str) -> str:
        """Convert a string to lowercase.

        Args:
            value: String to convert

        Returns:
            Lowercase string
        """
        return str(value).lower()

    @staticmethod
    def TRIM(value: str) -> str:
        """Remove leading and trailing whitespace from a string.

        Args:
            value: String to trim

        Returns:
            Trimmed string
        """
        return str(value).strip()

    @staticmethod
    def SUBSTRING(value: str, start: int, length: int | None = None) -> str:
        """Extract a substring from a string.

        Args:
            value: String to extract from
            start: Starting index (0-based)
            length: Optional length of substring

        Returns:
            Substring
        """
        if length is None:
            return str(value)[start:]
        return str(value)[start : start + length]

    @staticmethod
    def ABS(value: int | float) -> int | float:
        """Get the absolute value of a number.

        Args:
            value: Number

        Returns:
            Absolute value
        """
        return abs(value)

    @staticmethod
    def ROUND(value: int | float, digits: int = 0) -> int | float:
        """Round a number to specified decimal places.

        Args:
            value: Number to round
            digits: Decimal places (default 0)

        Returns:
            Rounded number
        """
        return round(value, digits)

    @staticmethod
    def MIN(*args: int | float) -> int | float:
        """Get the minimum value from arguments.

        Args:
            *args: Numbers to compare

        Returns:
            Minimum value
        """
        return min(args)

    @staticmethod
    def MAX(*args: int | float) -> int | float:
        """Get the maximum value from arguments.

        Args:
            *args: Numbers to compare

        Returns:
            Maximum value
        """
        return max(args)

    @staticmethod
    def COALESCE(*args: Any) -> Any:
        """Return the first non-null value from arguments.

        Args:
            *args: Values to check

        Returns:
            First non-null value, or None if all are null
        """
        for arg in args:
            if arg is not None:
                return arg
        return None


def evaluate_function(name: str, args: list[Any]) -> Any:
    """Evaluate a built-in function call.

    Args:
        name: Function name
        args: Function arguments

    Returns:
        Function result

    Raises:
        AttributeError: If function is not found
    """
    func = getattr(BuiltinFunctions, name, None)
    if func is None:
        raise AttributeError(f"Unknown function: {name}")
    return func(*args)
