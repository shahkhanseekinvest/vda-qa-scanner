# VDR QA Scanner

This repository contains the notebook `vdr_qa_local_fixed_V2.ipynb`, which implements a VDR (Virtual Data Room) QA scanning workflow.

The notebook is designed to:
- Load and preprocess VDR-like document data
- Run question/answer style checks over documents
- Produce outputs suitable for manual review and quality control

## Contents

- `vdr_qa_local_fixed_V2.ipynb` – main notebook for the QA scanning workflow

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/shahkhanseekinvest/vda-qa-scanner.git
   cd vda-qa-scanner
   ```
2. Create and activate a virtual environment (optional but recommended).
3. Install any Python dependencies you use in the notebook (e.g. via `pip install <package>`).
4. Open the notebook in Jupyter or VS Code and run the cells in order.

## Notes

- The exact dependencies depend on the libraries imported in the notebook.
- For production use, consider exporting the core logic into a Python module and adding tests.
