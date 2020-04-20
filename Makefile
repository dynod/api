# Makefile for dynod core api project

# Setup roots
WORKSPACE_ROOT := $(CURDIR)/../..
PROJECT_ROOT := $(CURDIR)
DEVENV_ROOT := $(WORKSPACE_ROOT)/tools/devenv

# Python package name
PYTHON_PACKAGE := dynod-api

# Python package for generated code
PYTHON_GEN_PACKAGE := dynod/api

# Main makefile suite - defs
include $(DEVENV_ROOT)/main.mk

# Default target is to build Python artifact
default: build

# Main makefile suite - rules
include $(DEVENV_ROOT)/rules.mk