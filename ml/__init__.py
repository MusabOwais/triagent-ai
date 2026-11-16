"""HackRx ML package (Role 1). Backend usage:

    from ml import predict_admission, flag_ecg, flag_xray

Each submodule loads its model once, on first import. Import at backend startup, not per request.
"""
__all__ = ["predict_admission", "flag_ecg", "flag_xray"]


def __getattr__(name):  # lazy: importing ml.admission alone does not pull in torch
    if name == "predict_admission":
        from .admission import predict_admission
        return predict_admission
    if name == "flag_ecg":
        from .ecg import flag_ecg
        return flag_ecg
    if name == "flag_xray":
        from .xray import flag_xray
        return flag_xray
    raise AttributeError(name)
