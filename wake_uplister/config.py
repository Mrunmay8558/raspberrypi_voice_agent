"""Wake-listener configuration re-exports.

The wake listener reads its defaults from the shared top-level configuration
module so runtime values stay consistent across the dashboard, voice bot, and
remote Daily client.
"""

from config import CHUNK_SIZE
from config import DEFAULT_COOLDOWN_SECS
from config import DEFAULT_INFERENCE_FRAMEWORK
from config import DEFAULT_PID_FILE
from config import DEFAULT_THRESHOLD
from config import DEFAULT_VAD_THRESHOLD
from config import DEFAULT_WAKEWORD_MODEL
from config import PROJECT_ROOT
from config import SAMPLE_RATE
