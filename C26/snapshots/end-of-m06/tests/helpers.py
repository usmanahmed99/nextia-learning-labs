from costmodel.demand import load_demand
from costmodel.design import load_design
from costmodel.inputs import load_measured, load_prices


def pack():
    """The design pack's own inputs: demand, design, measured values, prices."""
    return load_demand(), load_design(), load_measured(), load_prices()
