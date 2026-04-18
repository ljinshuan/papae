.PHONY: install test typecheck lint e2e clean help

VENV = .venv
PYTHON = uv run python
PYTEST = uv run pytest
PYRIGHT = uv run basedpyright
CLI = uv run gait-assess

VIDEO ?= data/test_data.mp4
OUTPUT ?= ./results

help:
	@echo "婴幼儿走路姿态评估系统 - 常用命令"
	@echo ""
	@echo "  make install     安装依赖（含开发依赖）"
	@echo "  make test        运行全部测试"
	@echo "  make typecheck   运行静态类型检查"
	@echo "  make lint        运行代码格式检查（ruff）"
	@echo "  make e2e         端到端验证（跳过 LLM）"
	@echo "  make e2e-full    端到端验证（含 LLM，需 API 密钥）"
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

clean:
	rm -rf $(OUTPUT)/ e2e_results/ .pytest_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
