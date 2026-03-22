"""
latency_logger.py — Voice Pipeline Latency Measurement

Measures and logs the time taken at each stage of the voice AI pipeline:

  Twilio webhook received
    → STT complete      (Twilio speech recognition done)
    → LLM complete      (OpenAI response generated)
    → response_ready    (TwiML assembled and ready to return)

Use this to identify bottlenecks. Target timings:
  STT  < 200ms   LLM  < 400ms   Total < 800ms

A module-level singleton (_current_tracker) holds the tracker for the
current HTTP request. Call start_new_turn() at the start of each Twilio
webhook to reset it.
"""

import time
import logging
from functools import wraps
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('latency')


class LatencyTracker:
    """
    Tracks elapsed time from webhook receipt through each pipeline stage.

    Usage:
        tracker = LatencyTracker(call_sid="CA123")
        tracker.start()
        # ... STT processing ...
        tracker.checkpoint('stt_complete')
        # ... OpenAI call ...
        tracker.checkpoint('llm_complete')
        # ... TwiML assembly ...
        tracker.checkpoint('response_ready')
        tracker.log_summary()
    """

    def __init__(self, call_sid=None):
        """
        Args:
            call_sid (str, optional): The Twilio Call SID for log correlation.
        """
        self.call_sid = call_sid
        self.start_time = None
        self.checkpoints = {}          # stage_name → elapsed ms from start
        self.webhook_received = None   # ISO timestamp when tracking began

    def start(self):
        """
        Record the start time (should be called immediately when the webhook fires).

        Returns:
            LatencyTracker: self, for method chaining.
        """
        self.start_time = time.time()
        self.webhook_received = datetime.utcnow().isoformat()
        self.checkpoints = {}
        return self

    def checkpoint(self, name):
        """
        Record the elapsed time from start to this point in the pipeline.

        Args:
            name (str): A label for this stage, e.g. "stt_complete", "llm_complete".

        Returns:
            float: Milliseconds elapsed since start().
        """
        if self.start_time is None:
            self.start()

        elapsed = (time.time() - self.start_time) * 1000  # ms
        self.checkpoints[name] = elapsed
        return elapsed

    def log_summary(self):
        """
        Log a summary of all checkpoints to the latency logger.

        Classifies the total response time as GOOD / ACCEPTABLE / SLOW and
        breaks down time per pipeline stage.

        Returns:
            dict or None: Summary dict with total_ms and category, or None
                          if no checkpoints have been recorded.
        """
        if not self.checkpoints:
            return None

        total_time = self.checkpoints.get('response_ready', 0)

        if total_time < 500:
            category = "GOOD"
        elif total_time < 1000:
            category = "ACCEPTABLE"
        else:
            category = "SLOW - needs optimization"

        summary = {
            'call_sid': self.call_sid,
            'webhook_received': self.webhook_received,
            'checkpoints': self.checkpoints,
            'total_ms': round(total_time, 2),
            'category': category
        }

        logger.info(f"LATENCY [{category}]: {summary}")

        # Log individual stage durations in order
        stages = []
        prev_time = 0
        for stage, time_ms in sorted(self.checkpoints.items(), key=lambda x: x[1]):
            stage_duration = time_ms - prev_time
            stages.append(f"{stage}: {round(stage_duration, 1)}ms")
            prev_time = time_ms

        logger.info(f"STAGES: {' → '.join(stages)}")

        return summary

    def get_metrics(self):
        """
        Return a flat dict of latency metrics suitable for storage or analytics.

        Returns:
            dict: Keys are call_sid, total_latency_ms, stt_latency_ms,
                  llm_latency_ms, tts_latency_ms.
        """
        return {
            'call_sid': self.call_sid,
            'total_latency_ms': self.checkpoints.get('response_ready', 0),
            'stt_latency_ms': self.checkpoints.get('stt_complete', 0),
            'llm_latency_ms': (
                self.checkpoints.get('llm_complete', 0) - self.checkpoints.get('stt_complete', 0)
                if 'llm_complete' in self.checkpoints else 0
            ),
            'tts_latency_ms': (
                self.checkpoints.get('response_ready', 0) - self.checkpoints.get('llm_complete', 0)
                if 'response_ready' in self.checkpoints else 0
            )
        }


# Module-level singleton — one tracker per active HTTP request
_current_tracker = None


def get_tracker(call_sid=None):
    """
    Return the active LatencyTracker, creating one if none exists.

    Args:
        call_sid (str, optional): If provided and the existing tracker belongs
                                  to a different call, a new tracker is created.

    Returns:
        LatencyTracker: The active tracker (auto-started if freshly created).
    """
    global _current_tracker
    if _current_tracker is None or (call_sid and _current_tracker.call_sid != call_sid):
        _current_tracker = LatencyTracker(call_sid)
        _current_tracker.start()
    return _current_tracker


def start_new_turn(call_sid=None):
    """
    Reset the module-level tracker for a new conversation turn.

    Call this at the top of every Twilio webhook handler so timing
    measurements are scoped to a single request/response cycle.

    Args:
        call_sid (str, optional): The Twilio Call SID for this turn.

    Returns:
        LatencyTracker: A fresh, started tracker.
    """
    global _current_tracker
    _current_tracker = LatencyTracker(call_sid)
    _current_tracker.start()
    return _current_tracker


def reset_tracker():
    """
    Clear the module-level tracker (e.g. after call ends or on error).
    """
    global _current_tracker
    _current_tracker = None


def log_latency(stage_name):
    """
    Decorator that records a checkpoint after the decorated function returns.

    Args:
        stage_name (str): The checkpoint label to record.

    Returns:
        Callable: The decorated function with latency tracking.

    Example:
        @log_latency('llm_complete')
        def call_openai(prompt):
            return openai_client.chat(...)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracker = get_tracker()
            result = func(*args, **kwargs)
            tracker.checkpoint(stage_name)
            return result
        return wrapper
    return decorator


# Reference guide printed during development/debugging
LATENCY_GUIDE = """
LATENCY INTERPRETATION:
========================
Total Response Time (webhook received → audio ready):
  < 500ms    = GOOD — feels responsive
  500–1000ms = ACCEPTABLE — slight delay but natural
  > 1000ms   = SLOW — noticeable lag, feels robotic

Stage Breakdown:
  STT (Speech-to-Text): Should be < 200ms
  LLM (Intent + Response): Should be < 400ms
  TTS (Text-to-Speech): Should be < 200ms

Common Bottlenecks:
  - Slow STT: Consider Deepgram or Whisper streaming
  - Slow LLM: Use GPT-4o-mini, cache common responses
  - Slow TTS: Consider ElevenLabs Flash or streaming TTS
"""


def print_latency_guide():
    """Print the latency interpretation reference guide to stdout."""
    print(LATENCY_GUIDE)
