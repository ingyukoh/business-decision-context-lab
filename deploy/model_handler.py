"""Private Lambda: real frozen Qwen generation; no adapter or external actions."""
import os, time, resource
from lab import LocalLLM, prompt_for, reviewed_output
_model = None

def handler(event, context):
    global _model
    started = time.perf_counter()
    cold = _model is None
    try:
        prompt, prediction = prompt_for(event['inputs'], event.get('include_context', True))
        if _model is None:
            _model = LocalLLM(os.environ.get('MODEL_PATH', '/var/task/model'))
        raw = _model.generate(prompt)
        return {'status': 'ok', 'prediction': prediction, **reviewed_output(raw, prediction),
                'model': 'Qwen/Qwen2.5-0.5B-Instruct', 'parameters': _model.parameter_count,
                'model_revision': '7ae557604adf67be50417f59c2c2f167def9a775',
                'fine_tuned': False, 'cold_model_load': cold,
                'compute_seconds': time.perf_counter() - started,
                'peak_process_memory_mib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                'generation_mode': 'live greedy generation; max 110 new tokens'}
    except Exception:
        # Never log inputs, prompts or outputs. Caller sees a bounded diagnostic.
        return {'status': 'unavailable', 'error': 'Model generation unavailable; use verified numeric prediction.',
                'compute_seconds': time.perf_counter() - started}
