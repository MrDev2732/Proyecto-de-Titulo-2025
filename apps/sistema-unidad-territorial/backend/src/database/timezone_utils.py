from datetime import datetime
import pytz


# Chile timezone
CHILE_TZ = pytz.timezone('America/Santiago')


def now_chile() -> datetime:
    """
    Get current datetime in Chile timezone.

    Returns:
        Current datetime with Chile timezone
    """
    return datetime.now(CHILE_TZ)

