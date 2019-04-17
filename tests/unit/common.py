from aiomock import AIOMock

_sentinel = object()


def _mocked_call(return_value=_sentinel):
    if return_value is _sentinel:
        return_value = AIOMock()
    func = AIOMock()
    func.async_return_value = return_value
    return func
