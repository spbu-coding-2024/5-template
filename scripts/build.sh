#!/bin/sh -e

BASEDIR=$(realpath "$(dirname "$0")")
ROOTDIR=$(realpath "$BASEDIR/..")

cmake -S . -B "$ROOTDIR/build"
cmake --build "$ROOTDIR/build"
