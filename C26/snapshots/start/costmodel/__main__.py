"""The design pack's calculator.

    python -m costmodel                 what the pack can calculate now (a summary)
    python -m costmodel inputs          the numbers in the input files, by kind
    python -m costmodel demand          demand per tenant (Module 1)
    python -m costmodel components      the architecture's parts (Module 2)
    python -m costmodel workload        workload arithmetic, every step (Module 3)
    python -m costmodel costs           monthly cost by driver (Module 3)
    python -m costmodel units           cost per question, document and tenant (Module 3)
    python -m costmodel scenarios       low, base and high, now and in month 12 (Module 3)
    python -m costmodel sensitivity     what if usage doubles, answers get longer ... (Module 3)
    python -m costmodel export          write costs.csv and explorer.json (Module 3)
    python -m costmodel options         routing, caching and batching (Module 4)
    python -m costmodel buildbuy        managed services or your own (Module 4)
    python -m costmodel recovery        RTO and RPO of two backup plans (Module 5)
    python -m costmodel growth          the growth signals month by month (Module 5)
    python -m costmodel check           check the whole design pack (Module 6)

Options: --scenario low|base|high (default base), --month N (default 0).
A command that belongs to a later module says so until you reach it.
"""

import argparse
import importlib
import sys

from .inputs import ROOT, InputError, load_measured, load_prices

LATER = {"demand": 1, "components": 2, "design": 3, "workload": 3, "costs": 3, "units": 3, "export": 3,
         "options": 4, "buildbuy": 4, "recovery": 5, "growth": 5, "packcheck": 6}


def need(module: str):
    try:
        return importlib.import_module(f"costmodel.{module}")
    except ModuleNotFoundError:
        raise SystemExit(f"This command arrives in Module {LATER[module]}. "
                         f"Download the end-of-module-{LATER[module]} snapshot or keep going.") from None


def model(args):
    d = need("demand").load_demand()
    g = need("design").load_design()
    return d, g, load_measured(), load_prices()


def cmd_inputs(args):
    p, m = load_prices(), load_measured()
    print(f"Prices:          {len(p):>3} (each with its source page)")
    print(f"Measured values: {len(m):>3} (each with the run it comes from)")
    try:
        verified, assumed = importlib.import_module("costmodel.demand").evidence_counts(
            importlib.import_module("costmodel.demand").load_demand())
        print(f"Demand values:   {verified + assumed:>3} ({verified} verified, {assumed} assumed)")
    except (ModuleNotFoundError, InputError) as e:
        print(f"Demand values:     0 ({e if isinstance(e, InputError) else 'fill in demand.toml in Module 1'})")


def cmd_demand(args):
    dm = need("demand")
    print(dm.demand_table(dm.load_demand(), args.month))


def cmd_components(args):
    c = need("components")
    print(c.components_table(c.load_components()))


def cmd_workload(args):
    d, g, m, p = model(args)
    w = need("workload").compute(d, g, m, args.scenario, args.month)
    print(need("workload").explain(w, m))


def cmd_costs(args):
    d, g, m, p = model(args)
    costs, w = need("costs").monthly(d, g, m, p, args.scenario, args.month)
    print(need("costs").cost_table(costs, f"Monthly cost, scenario {args.scenario}, month {args.month} "
                                          f"({w.tenants} tenants, {w.questions_per_month:,.0f} questions)"))


def cmd_units(args):
    d, g, m, p = model(args)
    un = need("units")
    print(un.unit_table(un.units(d, g, m, p, args.scenario, args.month),
                        f"Unit economics, scenario {args.scenario}, month {args.month}"))


def cmd_scenarios(args):
    d, g, m, p = model(args)
    print(need("units").scenarios(d, g, m, p))


def cmd_sensitivity(args):
    d, g, m, p = model(args)
    un = need("units")
    print(un.sensitivity_table(un.sensitivity(d, g, m, p, args.scenario)))


def cmd_export(args):
    d, g, m, p = model(args)
    ex = need("export")
    print(ex.write_csv(d, g, m, p, ROOT / "costs.csv"))
    print(ex.write_explorer(d, g, m, p, ROOT / "explorer.json"))


def cmd_options(args):
    d, g, m, p = model(args)
    op = need("options")
    print(op.routing_table(op.routing_rows(d, g, m, p, args.scenario)))
    print()
    print(op.caching_table(d, g, m, p, args.scenario))
    print()
    print(op.batching_table(m, p))


def cmd_buildbuy(args):
    d, g, m, p = model(args)
    bb = need("buildbuy")
    w = need("workload").compute(d, g, m, args.scenario, args.month)
    print(bb.buildbuy_table(m, p, bb.load_labour(), w.questions_per_month, args.scenario))


def cmd_recovery(args):
    d, g, m, p = model(args)
    rc = need("recovery")
    w = need("workload").compute(d, g, m, args.scenario, 12)
    used = sum(w.storage_gb.values()) - w.storage_gb["files"] + w.storage_growth_gb_per_month * 12
    print(rc.recovery_table(rc.load_recovery(), m, used, args.scenario))


def cmd_growth(args):
    d, g, m, p = model(args)
    gr = need("growth")
    print(gr.growth_table(gr.timeline(d, g, m, p, args.scenario), args.scenario))


def cmd_check(args):
    passed, lines = need("packcheck").run()
    print("\n".join(lines))
    if passed < len(need("packcheck").CHECKS):
        sys.exit(1)


def cmd_summary(args):
    cmd_inputs(args)
    for module, command in (("costs", cmd_costs), ("demand", cmd_demand)):
        try:
            importlib.import_module(f"costmodel.{module}")
        except ModuleNotFoundError:
            continue
        print()
        command(args)
        break
    else:
        print("\nNext: describe the users and fill in demand.toml (Module 1).")


COMMANDS = {name[4:]: f for name, f in globals().items() if name.startswith("cmd_")}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m costmodel", description="The design pack's calculator.")
    ap.add_argument("command", nargs="?", default="summary", choices=sorted(COMMANDS))
    ap.add_argument("--scenario", default="base", choices=("low", "base", "high"))
    ap.add_argument("--month", type=int, default=0)
    args = ap.parse_args(argv)
    try:
        COMMANDS[args.command](args)
    except InputError as e:
        raise SystemExit(f"Input problem: {e}") from None


if __name__ == "__main__":
    main()
