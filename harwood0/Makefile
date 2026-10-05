.PHONY: test test-cad test-firmware test-api cad render show firmware flash api api-sim lint

test: test-cad test-firmware test-api

test-cad:
	cd cad && uv run pytest -q

test-firmware:
	cd firmware && pio test -e native

test-api:
	cd api && uv run pytest -q

lint:
	cd cad && uv run ruff check . && uv run ruff format --check .
	cd api && uv run ruff check . && uv run ruff format --check .

cad:
	cd cad && uv run harwood0-cad

render:
	cd cad && uv run harwood0-render --all

show:
	cd cad && uv run harwood0-show

firmware:
	cd firmware && pio run -e uno_r4_wifi

flash:
	cd firmware && pio run -e uno_r4_wifi -t upload -t monitor

api:
	cd api && uv run harwood0-api

api-sim:
	cd api && HARWOOD0_ROBOT_URL=sim uv run harwood0-api
