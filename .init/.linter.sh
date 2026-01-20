#!/bin/bash
cd /home/kavia/workspace/code-generation/retro-resident-directory-202590-202599/resident_backend_api
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

