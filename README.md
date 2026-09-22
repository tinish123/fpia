# HO-FPIA: Field-Programmable Ising Array Accelerator Architecture Exploration with VPR

This repository contains the Python-based modeling workflow used to explore **HO-FPIA (High-Order Field-Programmable Ising Array)**, an FPGA-inspired architecture for mapping high-order K-SAT problems onto interconnected in-memory-computing (IMC) cores. Each core models locally connected forward and backward crossbar arrays, whereas a programmable routing fabric connects signals across cores. The goal is to exploit SAT problem sparsity and fan-in during packing and study architectural tradeoffs.

## Modeling flow

```text
SAT instance (CNF)
    → generate a BLIF connectivity model (LUTs and flip-flops)
    → render a parameterized VPR architecture (XML)
    → VPR: pack → place → route
    → parse implementation reports and estimate architecture metrics
    → optionally explore parameters with SMAC
```

The principal architecture parameters include IMC-core input/output capacity and routing connectivity (`I`, `O`, `FI`, `FO`). The analysis uses VPR mapping results to assess core utilization, routing requirements and area; timing and power results depend on the configured VPR models and input assumptions.

## Getting started

1. Clone this repository and install the Python packages imported by the notebooks. Use a Python environment with Jupyter, NumPy, Jinja2, and SMAC3; additional dependencies may be required by individual notebooks.
2. Obtain/build a **compatible VPR executable** separately (VPR 8.1.0-dev (commit f2783e2f8c)).
3. Obtain a compatible **VPR power technology file** if running power analysis (see https://docs.verilogtorouting.org/en/latest/vtr/power_estimation/)
4. Open the experiment notebook in `tests/`. In its configuration/setup cells, set the paths to **your VPR executable** and **power technology file**, along with any input/template/output paths required by the chosen experiment. Run the cells in order.

VPR, its power technology file, and any foundry-specific technology collateral are **not bundled** with this repository. Check the relevant notebook and source for the exact options and model assumptions used in a particular run.

## Related publication

T. Bhattacharya, G. H. Hutchinson, G. Pedretti, and D. Strukov, **“HO-FPIA: High-Order Field-Programmable Ising Arrays with In-Memory Computing,”** *IEEE ISVLSI*, pp. 252–259, 2024. [DOI: 10.1109/ISVLSI61997.2024.00054](https://doi.org/10.1109/ISVLSI61997.2024.00054).

The publication describes the proposed architecture, the SAT-to-VPR connectivity mapping, sparsity/fan-in-aware packing, and the area-modeling methodology. The software in this repository is intended for exploration and review; consult the paper for the published methodology and results.
