#!/bin/bash
if [ ! -f config ]; then
  cp config.example config.yaml
  echo "Created config file from template."
fi
