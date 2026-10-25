def compact(values):
    return {key: value for key, value in values.items() if value is not None}
