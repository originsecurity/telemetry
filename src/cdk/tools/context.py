import traceback

class AppContext(object):
    """Adapted from https://stackoverflow.com/a/1305682 and https://stackoverflow.com/a/20214464"""
    def __init__(self, d):
        for a, b in d.items():
            if isinstance(b, (list, tuple)):
                setattr(self, a, [AppContext(x) if isinstance(x, dict) else x for x in b])
            else:
                setattr(self, a, AppContext(b) if isinstance(b, dict) else b)

    def __iter__(self):
        for attr, value in self.__dict__.items():
            yield attr, value

    def items(self):
        return self.__dict__.items()

    def dict(self):
        return self.__dict__

def get_context(node):
    try:
        stage = node.try_get_context("stage")
        desired_count = node.try_get_context("desired_count")
        if stage == None:
            raise Exception("Stage variable not found; set with --context stage=stage_name")
        if desired_count == None:
            desired_count = 1
        stage_context = node.try_get_context(stage)
        shared_context = node.try_get_context("shared")
        result = merge(dict(stage_context), dict(shared_context))
        result["stage"] = stage
        result["default_desired_count"] = desired_count
        return AppContext(result)
    except Exception:
        error = traceback.format_exc()
        print(error)

def merge(a, b, path=None):
    """From https://stackoverflow.com/a/7205107"""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                pass # ignore conflicts, left dict wins.
        else:
            a[key] = b[key]
    return a
