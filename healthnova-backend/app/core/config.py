from app._pyc_loader import load_current_module

globals().update(load_current_module(__name__, __file__))
