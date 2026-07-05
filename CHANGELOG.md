# Changelog

## 0.1.0 - 2026-07-02

### Added

- First local OrderMind MVP.
- TXT/CSV/TSV/XLSX/XLSM order parsing.
- Rule template validation for required fields, item number format, unit, decimal places, line amount, total amount, and total quantity.
- Chinese and English UI.
- Local username/password sign-in.
- First sign-in password change flow.
- First-time use guide.
- Sample TXT and XLSX orders.
- Electron desktop shell with a packaged local Python backend.
- Mac zip package build for local customer trials.
- Desktop application icon resources for macOS and Windows packaging.
- Local HTML and Excel review report export from the result page.
- Sanitized customer-like sample orders for Chinese, English, Excel, and text-based PDF demos.
- One-click sample order review entries on the home page.
- Text-based PDF order parsing for PDFs that contain copyable text.
- Optional OCR fallback for scanned PDFs and image orders through a local OCR command.
- GitHub Actions installer build workflow for macOS and Windows packaging validation.
- Customer demo guide for running normal samples, issue samples, and report export.
- Release metadata and upgrade planning documents.

### Packaging Status

- Installable Mac and Windows packages are required for every customer trial release.
- A local Mac arm64 zip package can be produced with `npm run desktop:dist:mac`.
- Current Mac package output: `release/installers/OrderMind_0.1.0_mac_arm64.zip`.
- Windows packaging now has a CI build workflow, and still needs a successful Windows runner trial before customer distribution.
- macOS Developer ID signing and notarization remain pending until a signing certificate is available.
