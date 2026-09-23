"""ATS adapters for job application autofill."""
from .base import ATSAdapter
from .detector import detect_ats, get_adapter
from .greenhouse import greenhouse_adapter
from .lever import lever_adapter
from .ashby import ashby_adapter
from .workday import workday_adapter

# Registry of all adapters
ADAPTERS = {
    'greenhouse': greenhouse_adapter,
    'lever': lever_adapter,
    'ashby': ashby_adapter,
    'workday': workday_adapter,
}
