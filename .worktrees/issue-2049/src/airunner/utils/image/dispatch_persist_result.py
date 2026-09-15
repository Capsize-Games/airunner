from PySide6.QtCore import Qt, QMetaObject, Q_ARG


def dispatch_persist_result(scene_ref, future):
    scene = scene_ref()
    if scene is None:
        return
    try:
        payload = future.result()
    except Exception as exc:  # pragma: no cover - defensive
        payload = {"error": f"worker_exception:{exc}", "generation": 0}

    QMetaObject.invokeMethod(
        scene,
        "_handle_persist_result",
        Qt.QueuedConnection,
        Q_ARG(object, payload),
    )
