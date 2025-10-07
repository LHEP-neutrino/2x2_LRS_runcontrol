#!/bin/bash
if [ ! -f config ]; then
  # echo 'please renable me'
  cp config.example config.yaml
  echo "Created config file from template."
fi
