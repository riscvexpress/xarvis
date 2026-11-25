PYTHON_CONFIG_FILE:=${CURDIR}/rvx_config_python.mh

include ./rvx_init.mh

## keep the projects here out of this repository (.git/info/exclude, local only) ##
# shell commands that add /$p/ to .git/info/exclude, where $p is a directory name in ${CURDIR}
# (NOT ${MAKE}: a project checks share_python with 'make -q', which still runs ${MAKE} lines)
EXCLUDE_DIR_CMD = \
  exclude_file=$$(git rev-parse --git-path info/exclude) || exit 1; \
  mkdir -p "$$(dirname "$$exclude_file")" && touch "$$exclude_file" || exit 1; \
  if [ -s "$$exclude_file" ] && [ -n "$$(tail -c 1 "$$exclude_file")" ]; then echo >> "$$exclude_file"; fi; \
  if tr -d '\r' < "$$exclude_file" | grep -qxF "/$$p/"; then \
    echo "/$$p/ is in $$exclude_file already"; \
  elif git check-ignore -q "$$p"; then \
    echo "$$p is ignored already"; \
  else \
    echo "/$$p/" >> "$$exclude_file"; \
    echo "/$$p/ is added to $$exclude_file"; \
  fi; \
  if git ls-files --error-unmatch "$$p" >/dev/null 2>&1; then \
    echo "[WARNING] $$p is tracked here: run 'git rm -r --cached $$p' to stop tracking it"; \
  fi

# make exclude_project                  : every git repository right under here
# make exclude_project PROJECT=<name>   : only <name>
exclude_project:
	@if [ -n "${PROJECT}" ]; then \
	  list="${PROJECT}"; \
	else \
	  list=$$(for d in */; do [ -e "$${d}.git" ] && echo "$${d%/}"; done); \
	fi; \
	for p in $$list; do \
	  p=$${p%/}; \
	  if [ ! -d "$$p" ]; then echo "[FAIL] $$p is NOT a directory in ${CURDIR}"; exit 1; fi; \
	  ( ${EXCLUDE_DIR_CMD} ) || exit 1; \
	done

.PHONY: exclude_project

## share python with the projects here ##
# a project calls: make -C <this directory> share_python PYTHON_SHARE_FILE=<project>/rvx_config_python.mh
# a project right under here is also added to .git/info/exclude

share_python:
	@if [ -z "${PYTHON_SHARE_FILE}" ]; then \
	  echo "[FAIL] PYTHON_SHARE_FILE is required: make share_python PYTHON_SHARE_FILE=<project>/rvx_config_python.mh"; exit 1; \
	fi
	@if [ ! -f "${PYTHON_CONFIG_FILE}" ]; then \
	  echo "[FAIL] ${PYTHON_CONFIG_FILE} is NOT found: run 'make setup_python' in ${CURDIR}"; exit 1; \
	fi
	@tr -d '\r' < "${PYTHON_CONFIG_FILE}" | grep -vx "${PYTHON_MANUAL_MARKER}" > "${PYTHON_SHARE_FILE}"
	@echo "${PYTHON_CONFIG_FILE} is copied to ${PYTHON_SHARE_FILE}"
	@if d=$$(cd "$$(dirname "${PYTHON_SHARE_FILE}")" && pwd -P) && [ "$$(dirname "$$d")" = "$$(pwd -P)" ] && \
	    git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
	  p=$$(basename "$$d"); \
	  ( ${EXCLUDE_DIR_CMD} ) || echo "[WARNING] /$$p/ is NOT added to .git/info/exclude"; \
	fi

.PHONY: share_python
