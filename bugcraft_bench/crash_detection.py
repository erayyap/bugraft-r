"""Evaluator-only conservative crash and provider-block classification.

Report IDs are not signatures. Provider safety responses are recorded separately
from game failures; any explicitly authorized live continuation is logged.
"""
import re,json

MARKER = re.compile(
    r'---- Minecraft Crash Report ----|'
    r'# A fatal error has been detected by the Java Runtime Environment|'
    r'Crash report saved to',
    re.I,
)

# Keep these deliberately narrow: an ordinary in-game word such as "blocked"
# must not turn a game result into a provider result.  The returned names are
# stable evaluator metadata; provider response bodies are not copied into a
# result or reason string.
_PROVIDER_MARKERS = (
    ('cybersecurity_risk_flag', re.compile(r'\bflagged for possible cybersecurity risk\b', re.I)),
    ('content_flagged', re.compile(r'\bcontent was flagged\b', re.I)),
    ('content_policy', re.compile(r'\bcontent\s*[-_ ]?(?:filter|flag|moderation|policy)\b', re.I)),
    ('safety_policy', re.compile(r'\bsafety\s*[-_ ]?(?:filter|flag|moderation|policy|block)\b', re.I)),
    ('policy_violation', re.compile(r'\b(?:content|safety|provider)\s+policy\s+(?:violation|block(?:ed)?)\b', re.I)),
    ('request_blocked', re.compile(r'\b(?:request|response|completion|prompt|input|output)\s+(?:was\s+)?(?:blocked|rejected|refused)\b', re.I)),
    ('blocked_by_policy', re.compile(r'\b(?:blocked|rejected|refused)\s+by\s+(?:the\s+)?(?:provider|content|safety|policy|moderation)\b', re.I)),
)


def provider_block_signals(text=''):
    """Return stable names for explicit provider safety/content blocking text."""
    return [name for name, marker in _PROVIDER_MARKERS if marker.search(text)]


def provider_signals_from_events(lines):
    signals=set()
    for line in lines:
        try:event=json.loads(line)
        except json.JSONDecodeError:continue
        message=event.get('message',{})
        if event.get('type')=='message_end' and message.get('role')=='assistant' and message.get('stopReason')=='error':
            signals.update(provider_block_signals(message.get('errorMessage','')))
    return sorted(signals)


def classify(*, report='', logs='', signature=None, version_matches=False,
             process_exited=False, timed_out=False, setup_error=None,
             provider_blocked=False, hang_evidence=None):
    # A provider block means the evaluated model call was refused.  It is
    # intentionally checked before game evidence so it cannot be misreported
    # as a crash, timeout, or ordinary agent error.
    if provider_blocked:
        return {
            'outcome': 'provider_blocked',
            'reason': 'Provider ended with a safety/content block; see continuation log for any bounded retry',
        }
    if setup_error:
        return {'outcome': 'setup_blocked', 'reason': setup_error}
    crash = bool(MARKER.search(report + '\n' + logs))
    if crash:
        # Matching requires exception AND specific frame/context, never only a generic NPE.
        if signature and version_matches and signature.get('exception') and signature.get('context'):
            if signature['exception'] in report and all(s in report for s in signature['context']):
                return {'outcome': 'crash_match', 'reason': 'Fresh crash report matches version, exception and report-specific context; manual confirmation still required'}
        return {'outcome': 'unrelated_or_unconfirmed_crash', 'reason': 'Crash observed; target identity not established'}
    if hang_evidence and hang_evidence.get('status')=='window_hang_observed':
        return {'outcome':'hang_observed_unconfirmed_target','reason':hang_evidence['reason']}
    if hang_evidence and hang_evidence.get('status')=='reported_freeze_unconfirmed':
        return {'outcome':'freeze_reported_unconfirmed','reason':hang_evidence['reason']}
    if timed_out:
        return {'outcome': 'timeout', 'reason': 'Attempt time limit reached without confirmed crash/window-hang evidence'}
    if process_exited:
        return {'outcome': 'process_exit', 'reason': 'Exit alone is not crash evidence'}
    return {'outcome': 'no_crash', 'reason': 'No fresh crash or confirmed window-hang evidence; simulation-only freeze is not ruled out'}
