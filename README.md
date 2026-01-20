<div align="center">
  # 🏥 NHS GP IT System Extraction & Reconciliation
  
  **Extracting GP IT supplier data from national datasets and reconciling it with commissioner (ICB) data.**
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
  [![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)](https://www.python.org/)
  [![NHS Data](https://img.shields.io/badge/Data-NHS%20Digital-red)](https://digital.nhs.uk/)

  [📘 Read the User Guide](USER_GUIDE.md) | [🛠 Setup](USER_GUIDE.md#-getting-started) | [⚙️ How it Works](USER_GUIDE.md#-extraction--reconciliation-process)
</div>

---

## 🎯 The Objective

This project solves the challenge of consolidating disparate NHS data sources:

1.  **Extraction**: Harvests GP IT system data (TPP, EMIS, etc.) from the national "Appointments in General Practice" logs—a dataset otherwise difficult to query.
2.  **Reconciliation**: Automatically reconciles these practices with official commissioner (ICB) datasets, providing a unified view of systems under their respective commissioners.

## ✨ Key Capabilities

- ⚡ **High Performance**: Search over 6,000+ practices instantly by ODS code, name, or system type.
- 🎨 **Flexible Output**: Supports both human-readable text and machine-ready JSON.
- 📍 **ICB Mapping**: Automatic enrichment via the NHS ODS API.

---

## 🚀 Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Update to latest data
python execution/download_gpad.py

# 3. Lookup a practice
python execution/gp_lookup.py --ods-code A81001
```

**Example Output:**
```text
ODS Code: A81001
Name: THE DENSHAM SURGERY
Systems: TPP
Main System: TPP
```

---

## 📁 Project Structure (3-Layer Architecture)

```text
├── directives/       # Layer 1: SOPs and Instructions
├── execution/        # Layer 3: Deterministic Logic & Data
├── assets/           # Visual resources
├── .tmp/             # Intermediate processing area
└── USER_GUIDE.md     # Comprehensive documentation
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. This project follows the [Self-Annealing Loop](AGENTS.md#self-annealing-loop) principles for continuous improvement.

---

## 📜 License

This project is licensed under the MIT License. Data is sourced from NHS Digital and subject to [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

<div align="center">
  <sub>Made with ❤️ for healthcare integration</sub>
</div>
