.PHONY: install test typecheck lint e2e e2e-full clean viewer help

VENV = .venv
PYTHON = uv run python
PYTEST = uv run pytest
PYRIGHT = uv run basedpyright
CLI = uv run gait-assess

VIDEO ?= data/test_data.mp4
OUTPUT ?= ./results

help:
	@echo "婴幼儿姿态评估系统 - 常用命令"
	@echo ""
	@echo "  make install     安装依赖（含开发依赖）"
	@echo "  make test        运行全部测试"
	@echo "  make typecheck   运行静态类型检查"
	@echo "  make lint        运行代码格式检查（ruff）"
	@echo "  make e2e         端到端验证（跳过 LLM）"
	@echo "  make e2e-full    端到端验证（含 LLM，需 API 密钥）"
	@echo "  make viewer      运行 e2e 并自动打开 viewer.html"
	@echo "  make clean       清理结果和缓存"
	@echo "  make help        显示本帮助"

install:
	uv sync --extra dev
	uv pip install -e ".[dev]"

test:
	$(PYTEST) tests/ -v

typecheck:
	$(PYRIGHT) src/ tests/

lint:
	uv run ruff check src/ tests/

e2e:
	$(CLI) --video $(VIDEO) --output $(OUTPUT) --skip-llm

e2e-full:
	$(CLI) --video $(VIDEO) --output $(OUTPUT)

viewer: e2e
	@echo "启动 HTTP 服务器并打开交互式查看器..."
	@cd $(OUTPUT) && python3 -m http.server 8080 &
	@sleep 2
	@open http://localhost:8080/viewer.html || xdg-open http://localhost:8080/viewer.html || echo "请手动打开 http://localhost:8080/viewer.html"

clean:
	rm -rf $(OUTPUT)/ e2e_results/ .pytest_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
