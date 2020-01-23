# General Makefile for interfaces code generation
.SILENT:

# Preliminary checks
PROTOC := $(shell which protoc || true)
ifeq ($(PROTOC),)
$(error "protoc" is not installed)
endif

# Some paths & defs
GEN := gen
PROTOS := protos
PYTHON_GEN := $(GEN)/python
PROTO_BUILD := $(PROTOC) --proto_path=$(PROTOS)

# Inputs/outputs
APIS := $(shell find $(PROTOS) -name *.proto)
PYTHON_INTERFACES := $(foreach API,$(APIS),$(PYTHON_GEN)/$(subst $(PROTOS)/,,$(subst .proto,,$(API)))_pb2.py)

# Targets
.PHONY: all clean

all: $(PYTHON_INTERFACES)

clean:
	rm -f $(PYTHON_INTERFACES)

# Code generation for:
# - Python
$(PYTHON_GEN)/%_pb2.py: $(PROTOS)/%.proto
	$(PROTO_BUILD) --python_out=$(PYTHON_GEN) $<
