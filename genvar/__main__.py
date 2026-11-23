"""`python -m genvar` ouvre OGIAS (interface web locale) comme `python -m sorep_web`."""
import runpy

runpy.run_module("sorep_web", run_name="__main__")
