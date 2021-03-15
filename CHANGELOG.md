# Changelog

All notable changes to this project should be documented in this file.

The format is based on [Keep a
Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.15] - 2020-03-15

- added logging of user agent header to request StarletteTracingMiddleware
- reformatted all code using black formatter

## [0.8.14] - 2020-01-15

- removed usage of walrus operator in order to be python 3.6 compatible

## [0.8.13] - 2020-01-15

### Added

- Logging of user-id
  - user-id is picked up from incoming http header User-Id and added to LogContext
  - Outgoing requests also send User-Id header if user_id is present in LogContext

## [0.8.12] - 2020-01-07

### Added

- Some README text briefly describing the project.
- MIT license.
- Changelog!
