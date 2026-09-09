"""One explicit live-session continuation, with original deadline and context.

Never restarts a world or changes provider, prompts, model, or safeguards. The
only additional user message is the user-approved literal `continue.`. Original
provider errors remain in the native session and evidence transcript.
"""
from .crash_detection import provider_block_signals
POLICY='one-live-cybersecurity-flag-continuation-v1'
NUDGE='continue.'
MAX_NUDGES=1

def eligible(*,terminal_error,used,remaining,session_exists,stop_reason):
    return (used<MAX_NUDGES and remaining>0 and session_exists
            and stop_reason=='agent_completed'
            and 'cybersecurity_risk_flag' in provider_block_signals(terminal_error or ''))
