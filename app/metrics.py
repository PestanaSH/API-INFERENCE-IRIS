"""
Custom Metrics with Prometheus
Defines counters, histograms, and gauges for monitoring

Prometheus collects numerical metrics that allow:

* Real-time performance monitoring
* Creating automated alerts
* Visualizing dashboards in Grafana

Types of metrics:

* Counter: Only increases (total requests, errors)
* Histogram: Distribution of values (latency, size)
* Gauge: Goes up and down (active users, memory)
"""
from prometheus_client import Counter, Histogram, Gauge

# =============================================================================
# COUNTERS
# Count events that only increase (never decrease)
# Useful for: total requests, errors, logins
# =============================================================================

# Total number of predictions made
# Labels allow filtering by class and user

PREDICTIONS_TOTAL = Counter(
    'iris_predictions_total',
    'Total de predicoes realizadas',
    ['classe', 'user']  # Labels para filtrar no Prometheus/Grafana
)

# Example: PREDICTIONS_TOTAL.labels(class="setosa", user="admin").inc()
# Batch predictions
BATCH_PREDICTIONS_TOTAL = Counter(
    'iris_batch_predictions_total',
    'Total de predicoes em lote',
    ['user', 'batch_size']
)

# Login attempts (success/failure)
LOGIN_ATTEMPTS = Counter(
    'login_attempts_total',
    'Total de tentativas de login',
    ['status']  # success ou failed
)
# Exemplo: LOGIN_ATTEMPTS.labels(status="success").inc()

# Erros por tipo
ERRORS_TOTAL = Counter(
    'api_errors_total',
    'Total de erros',
    ['endpoint', 'error_type']
)

# Rate limit excedido
RATE_LIMIT_EXCEEDED = Counter(
    'rate_limit_exceeded_total',
    'Total de requisicoes bloqueadas por rate limit',
    ['endpoint', 'client_ip']
)

PREDICTION_LATENCY = Histogram(
    'iris_prediction_latency_seconds',
    'Latencia das predicoes em segundos',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5]
)

BATCH_PREDICTION_LATENCY = Histogram(
    'iris_batch_prediction_latency_seconds',
    'Latencia das predicoes em lote',
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUEST_LATENCY = Histogram(
    'http_request_latency_seconds',
    'Latencia das requisicoes HTTP',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

MODEL_LOADED = Gauge(
    'model_loaded',
    'Indica se o modelo esta carregado (1) ou nao (0)'
)

AVG_CONFIDENCE = Gauge(
    'prediction_avg_confidence',
    'Confianca media das ultimas predicoes'
)