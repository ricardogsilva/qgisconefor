# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

- Update docs


## [2.0.0-rc1] - 2024-07-17
- Ported code to Python3 and QGIS v3
- Added Changelog
- Moved to src layout
- Converted README to markdown
- Manage dev workflows with pluginadmin
- Move business logic outside of plugin dialog
- Measure areas using QGIS project's ellipsoid
- Use Processing algorithm also for powering dialog-based execution 
- Generation of Conefor inputs can be cancelled by the user
- Use QgsTask and QgsTaskManager instead of QThreads with locks
- Use QgsDistanceArea for area and distance calculations
- Use QgsMessageBar for communication instead of a custom QLabel


## [1.2.1] - 2015-06-13

### Changed
- Fixed bugs


## [1.2] - 2015-06-10

### Changed
- Adapted code to run with QGIS v2.8


## 1.1.0 - ???

### Changed
- Adapted code to cope with Processing API changes

## 1.0.0 - ???

### Added
- First stable release

[unreleased]: https://github.com/ricardogsilva/qgisconefor/compare/v1.2.1...main
[2.0.0-rc1]: https://github.com/ricardogsilva/qgisconefor/compare/v2.0.0-rc1...main
[1.2.1]: https://github.com/ricardogsilva/qgisconefor/compare/v1.2...v1.2.1
[1.2]: https://github.com/kartoza/qgis_geonode/releases/tag/v1.2
