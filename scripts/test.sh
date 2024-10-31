#!/bin/sh -e

BASEDIR=$(realpath "$(dirname "$0")")
ROOTDIR=$(realpath "$BASEDIR/..")
BINDIR=$(realpath "$ROOTDIR/build/src")
TESTDIR=$(realpath "$ROOTDIR/test")

echo "Test comparer"
python3 "${TESTDIR}/comparer/checker.py" "${BINDIR}/comparer" "${TESTDIR}/comparer/test_data"

echo "Test converter"
python3 "${TESTDIR}/converter/checker.py" "${BINDIR}/converter" "${TESTDIR}/converter/test_data" "${BINDIR}/comparer"
