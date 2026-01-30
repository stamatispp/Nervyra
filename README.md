# 🧩 Nervyra – Clause Checker

**Nervyra** is a secure, desktop-based clause recognition and matching application built with **PySide6 (Qt for Python)** for use within **Fenchurch Faris Ltd.**  
It analyzes insurance policy clauses and automatically matches them against reinsurer-specific JSON libraries (e.g., Zurich, QBE, SwiftRE, Kiln).

---

## 🚀 Key Features

- 🔐 **User Authentication**
  - Local or shared `users.json` login system (`U:\IT\APP\Nervyra`)
  - PBKDF2-SHA256 password hashing with salt
  - Admin-only interface for creating and managing users

- 🏢 **Department-Based Routing**
  - Departments: Property / Special Risks, Liability, Life / PA & Medical, Financial Lines, PI, Administration
  - Automatic loading of reinsurer data files (e.g., `Property_Zurich.json`, `Liability_Kiln.json`)

- 🧠 **Clause Matching Engine**
  - Token-based matching using singular/plural normalization
  - Filters out timing/boilerplate words
  - Ignores specific wording (e.g., *LM7*, *Temporary*, *Payment Warranty*)

- 🪶 **User Interface**
  - Multi-step workflow: **Login → Select Reinsurer → Analyze Text → Compare → Final Review**
  - Blue highlighting for autocompleted clauses
  - Strike-through visual for rejected/overridden text
  - Export to clipboard in **RTF + HTML** for Word compatibility

- 🧰 **Admin Console**
  - Available only to users in the *Administration* department
  - Create, overwrite, or remove user records securely


---

## ⚙️ Tech Stack

- **Python 3.11+**
- **PySide6 (Qt 6)** for GUI
- **JSON** for data storage
- **hashlib / binascii** for secure credential hashing
- **PBKDF2** password protection

---

## 🧰 Developer Notes

To run locally (for development):

```bash
pip install PySide6
python main.py


---

© 2025 Fenchurch Faris Ltd. – Developed by Stamatis Papadimitriou


