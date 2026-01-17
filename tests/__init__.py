"""
Leveredge Integration Test Suite.

This package contains integration tests for the Leveredge multi-agent infrastructure.

Test Categories:
- test_health.py       - Comprehensive health checks for all agents
- test_atlas.py        - ATLAS orchestration tests
- test_aegis.py        - Credential management tests
- test_event_bus.py    - Event publishing/subscribing tests
- test_creative_fleet.py - Creative Fleet tests (MUSE, CALLIOPE, THALIA, ERATO, CLIO)
- test_security_fleet.py - Security Fleet tests (CERBERUS, PORT-MANAGER)

Usage:
    # Run all tests
    ./run_tests.sh

    # Run specific category
    ./run_tests.sh health
    ./run_tests.sh core
    ./run_tests.sh creative
    ./run_tests.sh security

    # Run with coverage
    ./run_tests.sh coverage
"""
