# Makefile for dynod core api project

# Setup roots
WORKSPACE_ROOT := $(CURDIR)/../..
PROJECT_ROOT := $(CURDIR)

# Python package name
PYTHON_PACKAGE := dynod-commons

# Package for generated code
PROTO_PACKAGE := dynod_commons/api

# Dependencies on grpc-helper api
PROTO_DEPS := $(WORKSPACE_ROOT)/apis/grpc-helper/protos

# Main makefile suite - defs
include $(WORKSPACE_ROOT)/.workspace/main.mk

# Default target is to build Python artifact
default: build

# Main makefile suite - rules
include $(WORKSPACE_ROOT)/.workspace/rules.mk
