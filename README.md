🧩 Nervyra – Clause Checker (v1.1.2)

Nervyra Clause Checker v1.1.2 is an enhanced, secure desktop-based clause recognition and matching application built with PySide6 (Qt for Python) for internal use within Fenchurch Faris Ltd.

This version improves clause detection accuracy, workflow stability, and reinsurer library support, allowing underwriters and brokers to validate policy wording against reinsurer-specific clause databases (Zurich, QBE, SwiftRE, Kiln, and more).

🚀 Key Features (v1.1.2)
🔐 Secure User Authentication

Centralized users.json login system stored locally or on shared drive (U:\IT\APP\Nervyra)

Strong password protection using PBKDF2-SHA256 hashing + salt

Role-based access with Admin-only user management

🏢 Department & Reinsurer Routing

Built-in department classification:

Property / Special Risks

Liability

Life / PA & Medical

Financial Lines

PI

Administration

Automatically loads the correct reinsurer clause libraries such as:

Property_Zurich.json

Liability_Kiln.json

FinancialLines_QBE.json

🧠 Improved Clause Matching Engine

Token-based clause recognition with smarter keyword matching

Singular/plural normalization for better detection accuracy

Filters out boilerplate and timing-based words

Ignores irrelevant policy wording patterns such as:

LM7

Temporary

Payment Warranty

Supports clause matching even from minimal user input

🪶 Updated User Workflow Interface

Multi-step guided process:

Login → Select Reinsurer → Analyze Text → Clause Comparison → Final Review

UI enhancements include:

Blue highlighting for autocompleted clause text

Editable override before final confirmation

Strike-through visualization for rejected clauses

Clear separation between:

Matched clauses list

Clause description review

📋 Export & Word Compatibility

Export results directly to clipboard

Supports both:

RTF

HTML formatting

Ensures seamless pasting into Microsoft Word templates

🧰 Administration Console (Restricted)

Available only to users in the Administration department:

Create new users securely

Overwrite existing records

Remove users safely

Maintain internal access control compliance

⚙️ Tech Stack

Python 3.11+

PySide6 (Qt 6 GUI Framework)

JSON-based clause libraries

hashlib / binascii for credential encryption

PBKDF2 secure authentication system

🧰 Developer Notes (v1.1.2)

To run locally for development:

pip install PySide6
python main.py

📌 Version Highlights – v1.1.2

Improved clause matching reliability

Cleaner review screen output

Editable clause confirmation workflow

Better reinsurer JSON handling

Stability improvements for internal deployment

© 2025 Fenchurch Faris Ltd.
Developed by Stamatis Papadimitriou
