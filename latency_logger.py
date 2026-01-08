"""
Latency Logger for Voice AI Pipeline
Measures timing from STT → LLM → TTS to identify bottlenecks.
"""
import time
import logging
from functools import wraps
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('latency')

class LatencyTracker:
    """Track latency across the voice AI pipeline."""
    
    def __init__(self, call_sid=None):
        self.call_sid = call_sid
        self.start_time = None
        self.checkpoints = {}
        self.webhook_received = None
    
    def start(self):
        """Mark the start of processing (webhook received)."""
        self.start_time = time.time()
        self.webhook_received = datetime.utcnow().isoformat()
        self.checkpoints = {}
        return self
    
    def checkpoint(self, name):
        """Record a checkpoint with elapsed time from start."""
        if self.start_time is None:
            self.start()
        
        elapsed = (time.time() - self.start_time) * 1000  # Convert to ms
        self.checkpoints[name] = elapsed
        return elapsed
    
    def log_summary(self):
        """Log a summary of all checkpoints."""
        if not self.checkpoints:
            return
        
        total_time = self.checkpoints.get('response_ready', 0)
        
        # Categorize latency
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
        
        # Log individual stage times
        stages = []
        prev_time = 0
        for stage, time_ms in sorted(self.checkpoints.items(), key=lambda x: x[1]):
            stage_duration = time_ms - prev_time
            stages.append(f"{stage}: {round(stage_duration, 1)}ms")
            prev_time = time_ms
        
        logger.info(f"STAGES: {' → '.join(stages)}")
        
        return summary
    
    def get_metrics(self):
        """Get metrics dict for storage/analytics."""
        return {
            'call_sid': self.call_sid,
            'total_latency_ms': self.checkpoints.get('response_ready', 0),
            'stt_latency_ms': self.checkpoints.get('stt_complete', 0),
            'llm_latency_ms': self.checkpoints.get('llm_complete', 0) - self.checkpoints.get('stt_complete', 0) if 'llm_complete' in self.checkpoints else 0,
            'tts_latency_ms': self.checkpoints.get('response_ready', 0) - self.checkpoints.get('llm_complete', 0) if 'response_ready' in self.checkpoints else 0
        }


# Global tracker for current request (simple approach)
_current_tracker = None

def get_tracker(call_sid=None):
    """Get or create a latency tracker for the current request."""
    global _current_tracker
    if _current_tracker is None or (call_sid and _current_tracker.call_sid != call_sid):
        _current_tracker = LatencyTracker(call_sid)
        _current_tracker.start()  # Auto-start on creation
    return _current_tracker

def start_new_turn(call_sid=None):
    """Start a new turn - resets tracker for fresh timing."""
    global _current_tracker
    _current_tracker = LatencyTracker(call_sid)
    _current_tracker.start()
    return _current_tracker

def reset_tracker():
    """Reset the current tracker."""
    global _current_tracker
    _current_tracker = None

def log_latency(stage_name):
    """Decorator to log latency for a function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracker = get_tracker()
            result = func(*args, **kwargs)
            tracker.checkpoint(stage_name)
            return result
        return wrapper
    return decorator


# Interpretation guide
LATENCY_GUIDE = """
LATENCY INTERPRETATION:
========================
Total Response Time (webhook received → audio ready):
  < 500ms  = GOOD - feels responsive
  500-1000ms = ACCEPTABLE - slight delay but natural
  > 1000ms = SLOW - noticeable lag, feels robotic

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
    """Print the latency interpretation guide."""
    print(LATENCY_GUIDE)
