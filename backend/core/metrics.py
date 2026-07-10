"""
core/metrics.py — كل الـ Prometheus metrics المخصصة للمشروع في مكان واحد.

بتتسجل هنا مرة واحدة بس، وأي ملف تاني (llm/client.py, core/utils.py,
routers/messages.py) بيستوردها من هنا بدل ما يعرّفها من جديد.
لو عرّفناها في أكتر من مكان، Prometheus هيرمي:
"Duplicated timeseries in CollectorRegistry".
"""
from prometheus_client import Gauge, Counter, Histogram

# حالة الموديل: 0=loading 1=idle 2=processing 3=error
model_status_gauge = Gauge(
    "llm_model_status",
    "Current LLM model status (0=loading 1=idle 2=processing 3=error)",
)

# هل فيه توليد شغال دلوقتي؟
model_busy_gauge = Gauge(
    "llm_model_busy",
    "1 if the model is currently generating a response, else 0",
)

# كام مرة اترفض طلب بسبب انشغال الموديل (423 Locked)
busy_rejections_total = Counter(
    "llm_busy_rejections_total",
    "Number of requests rejected with 423 because the model was busy",
)

# زمن توليد الرد بالكامل (من أول توكين لآخر توكين)
inference_duration_seconds = Histogram(
    "llm_inference_duration_seconds",
    "Total time to generate a full response",
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120),
)

# زمن أول توكين
time_to_first_token_seconds = Histogram(
    "llm_time_to_first_token_seconds",
    "Latency from request start until the first token is streamed",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10),
)

# إجمالي التوكينز المولّدة
tokens_generated_total = Counter(
    "llm_tokens_generated_total",
    "Total number of tokens generated across all responses",
)

# أخطاء أثناء الـ streaming - كانت قبل كده بتختفي تماماً (except: pass)
stream_errors_total = Counter(
    "llm_stream_errors_total",
    "Number of inference errors that occurred mid-stream",
)
