"""
Prediction routes (single and batch).
"""
import time

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import get_current_user
from app.core import logger
from app.metrics import (
    BATCH_PREDICTION_LATENCY,
    BATCH_PREDICTIONS_TOTAL,
    PREDICTION_LATENCY,
    PREDICTIONS_TOTAL,
)
from app.model_loader import MODELO_OK, classes, modelo
from app.rate_limit import BATCH_RATE_LIMIT, PREDICT_RATE_LIMIT, limiter
from app.schemas import (
    BatchPredictItem,
    BatchPredictRequest,
    BatchPredictResponse,
    IrisRequest,
    IrisResponse,
)


router = APIRouter(tags=["Predicao"])


@router.post("/predict", response_model=IrisResponse)
@limiter.limit(PREDICT_RATE_LIMIT)
def predict(
    request: Request,
    payload: IrisRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Makes a prediction for a single Iris Flower.

    Rate limit: 30 requests per minute

    Authentication required: Include the Authorization: Bearer <token> header
    """
    if not MODELO_OK:
        raise HTTPException(status_code=503, detail="Modelo nao disponivel")

    trace_id = getattr(request.state, "trace_id", "N/A")
    start = time.perf_counter()

    features = np.array(
        [
            [
                payload.sepal_length,
                payload.sepal_width,
                payload.petal_length,
                payload.petal_width,
            ]
        ]
    )

    pred_idx = modelo.predict(features)[0]
    probs = modelo.predict_proba(features)[0]
    classe = classes[pred_idx]
    confidence = float(max(probs))

    latency = time.perf_counter() - start

    PREDICTIONS_TOTAL.labels(classe=classe, user=current_user["username"]).inc()
    PREDICTION_LATENCY.observe(latency)

    logger.info(
        "prediction_completed",
        extra={
            "trace_id": trace_id,
            "user": current_user["username"],
            "classe": classe,
            "confidence": round(confidence, 4),
            "latency_ms": round(latency * 1000, 2),
        },
    )

    return IrisResponse(
        sucesso=True,
        classe=classe,
        probabilidades={classes[i]: round(float(p), 4) for i, p in enumerate(probs)},
        usuario=current_user["username"],
    )


@router.post("/predict/batch", response_model=BatchPredictResponse)
@limiter.limit(BATCH_RATE_LIMIT)
def predict_batch(
    request: Request,
    payload: BatchPredictRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Makes predictions for multiple Iris flowers at once.

    **Rate Limit:** 10 requests per minute

    **Maximum:** 100 flowers per request

    **Authentication required:** Include the `Authorization: Bearer <token>` header

    **Batch Advantages:**

    * More efficient than multiple individual calls
    * Lower network overhead
    * Ideal for bulk processing
    """
    if not MODELO_OK:
        raise HTTPException(status_code=503, detail="Modelo nao disponivel")

    trace_id = getattr(request.state, "trace_id", "N/A")
    start = time.perf_counter()

    features_list = [
        [
            item.sepal_length,
            item.sepal_width,
            item.petal_length,
            item.petal_width,
        ]
        for item in payload.items
    ]
    features = np.array(features_list)

    pred_indices = modelo.predict(features)
    all_probs = modelo.predict_proba(features)

    predicoes = []
    for i, (pred_idx, probs) in enumerate(zip(pred_indices, all_probs)):
        classe = classes[pred_idx]
        confidence = float(max(probs))

        predicoes.append(
            BatchPredictItem(
                indice=i,
                classe=classe,
                confianca=round(confidence, 4),
                probabilidades={
                    classes[j]: round(float(p), 4) for j, p in enumerate(probs)
                },
            )
        )

        PREDICTIONS_TOTAL.labels(classe=classe, user=current_user["username"]).inc()

    latency = time.perf_counter() - start
    batch_size = len(payload.items)

    BATCH_PREDICTIONS_TOTAL.labels(
        user=current_user["username"], batch_size=str(batch_size)
    ).inc()
    BATCH_PREDICTION_LATENCY.observe(latency)

    logger.info(
        "batch_prediction_completed",
        extra={
            "trace_id": trace_id,
            "user": current_user["username"],
            "batch_size": batch_size,
            "latency_ms": round(latency * 1000, 2),
            "avg_latency_per_item_ms": round((latency * 1000) / batch_size, 2),
        },
    )

    return BatchPredictResponse(
        sucesso=True,
        total=batch_size,
        tempo_total_ms=round(latency * 1000, 2),
        predicoes=predicoes,
        usuario=current_user["username"],
    )
