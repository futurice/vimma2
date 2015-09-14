import importlib
import itertools

def subclasses(c):
    return list(itertools.chain.from_iterable(map(subclasses, c.__subclasses__()))) or c.__subclasses__()

def get_import(module, thing):
    m = importlib.import_module(module)
    return getattr(m, thing)
