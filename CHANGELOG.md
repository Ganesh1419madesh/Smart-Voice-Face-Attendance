## [Unreleased] - 2023-05-11

### Added
- Added a "Train Model" feature to the dashboard that allows the user to retrain the face recognition model with a single click
- Added support for generating Excel reports for daily attendance, date range attendance, and per-student attendance
- Added a "Reports" page to the dashboard to provide access to the new reporting features
- Added support for configuring various settings like face recognition tolerance, voice sample count, and attendance cooldown period via a `config.py` file
- Added a Vercel deployment configuration to allow hosting the application on Vercel's serverless platform

### Changed
- Restructured the project to follow a more modular and maintainable file/folder organization
- Improved the overall user interface and responsiveness of the web dashboard
- Updated the README.md file to provide more detailed instructions for installation, configuration, and usage

### Fixed
- Resolved an issue where the voice recognition model was not being properly trained or loaded, preventing voice-based attendance marking

## [1.0.0] - 2022-11-15

### Added
- Initial release of the Smart Attendance System
- Implemented face recognition-based attendance marking using the `face_recognition` library
- Implemented voice recognition-based attendance marking using `librosa` and `scikit-learn`
- Provided a web-based dashboard for student registration, attendance marking, and attendance history
- Integrated a SQLite database to store student information and attendance records
- Included features for student management, such as search, view, and delete operations

---
<!-- pushpen-footer -->
Documentation automatically generated and kept up to date by [Pushpen](https://pushpen.dev).
