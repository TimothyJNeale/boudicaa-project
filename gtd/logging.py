# SDS 9.2 — JSON log formatter
import json
import logging
import traceback
import uuid


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'reference_id': str(uuid.uuid4())[:8],
            'timestamp': self.formatTime(record),
            'severity': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }

        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_path'):
            log_entry['request_path'] = record.request_path
        if hasattr(record, 'request_method'):
            log_entry['request_method'] = record.request_method

        if record.exc_info:
            log_entry['exception_type'] = record.exc_info[0].__name__
            log_entry['stack_trace'] = traceback.format_exception(*record.exc_info)

        return json.dumps(log_entry)
