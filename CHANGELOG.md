## [Unreleased] - 2023-05-28

### Added
- Added manual model training trigger from the dashboard
- Added Vercel deployment configuration for the Flask API

### Changed
- Restructured the project to have a top-level `main.py` file that launches the nested Smart Attendance System project
- Updated the Smart Attendance System README.md file with more detailed project structure and installation instructions

### Fixed
- No fixes included in this release

### Removed
- No removals included in this release

## [1.0.0] - 2023-05-01

### Added
- Initial version of the Smart Attendance System with the following features:
  - Student registration with face image capture
  - Face-based and voice-based attendance marking
  - Daily, date-range, and per-student attendance reports
  - Student management (search, view, delete)
  - One-click face model training
  - Admin login with SQLite-backed authentication
- Detailed project structure and usage instructions in the README.md file
- Configuration options in the `config.py` file to customize the system

---
<!-- pushpen-footer -->
Documentation automatically generated and kept up to date by [Pushpen](https://pushpen.dev).
