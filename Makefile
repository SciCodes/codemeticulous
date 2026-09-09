.DEFAULT_GOAL := help

.PHONY: help sync lock lock-check test format format-check check build

UV ?= uv
BLACK_EXCLUDE ?= codemeticulous/(cff|datacite)/models\.py

help:
	@echo "Common targets:"
	@echo "  make sync         - install locked project and development dependencies"
	@echo "  make lock         - update the dependency lockfile"
	@echo "  make test         - run the test suite"
	@echo "  make format       - format Python sources and tests"
	@echo "  make format-check - check Python formatting without changing files"
	@echo "  make check        - validate the lockfile and run the test suite"
	@echo "  make build        - run checks and build source/wheel distributions"

sync:
	$(UV) sync --locked --all-extras --dev

lock:
	$(UV) lock

lock-check:
	$(UV) lock --check

test:
	$(UV) run --frozen python -m pytest

format:
	$(UV) run --frozen black --extend-exclude '$(BLACK_EXCLUDE)' codemeticulous tests

format-check:
	$(UV) run --frozen black --check --extend-exclude '$(BLACK_EXCLUDE)' codemeticulous tests

check: lock-check test

build: check
	$(UV) build
