# General Makefile for interfaces code generation
.SILENT:

# Preliminary checks
PROTOC := $(shell which protoc || true)
ifeq ($(PROTOC),)
$(error "protoc" is not installed)
endif

# Some paths & defs
PROTOS := protos
PYTHON := python
PYTHON_GEN := $(PYTHON)/src/stuffnodes/api
PROTO_BUILD := $(PROTOC) --proto_path=$(PROTOS)

# Inputs/outputs
APIS := $(shell find $(PROTOS) -name *.proto)
PYTHON_INTERFACES := $(foreach API,$(APIS),$(PYTHON_GEN)/$(subst $(PROTOS)/,,$(subst .proto,,$(API)))_gen.py)

# Targets
.PHONY: all clean

all: $(PYTHON_INTERFACES)

clean:
	rm -f $(PYTHON_INTERFACES)

# Code generation for:
# - Python
$(PYTHON_GEN)/%_gen.py: $(PROTOS)/%.proto
	$(PROTO_BUILD) --python_out=$(PYTHON_GEN) $<
	mv $(subst _gen,_pb2,$@) $@
