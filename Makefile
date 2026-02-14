.PHONY: help install uninstall test clean lint format docs update

# 默认目标
help:
	@echo "AI CLI - Makefile 命令"
	@echo ""
	@echo "使用: make [目标]"
	@echo ""
	@echo "目标:"
	@echo "  install     - 安装 AI CLI"
	@echo "  uninstall   - 卸载 AI CLI"
	@echo "  test        - 运行测试"
	@echo "  clean       - 清理缓存文件"
	@echo "  lint        - 代码检查"
	@echo "  format      - 格式化代码"
	@echo "  docs        - 生成文档"
	@echo "  update      - 更新程序"
	@echo "  version     - 显示版本信息"

# 安装
install:
	@echo "安装 AI CLI..."
	./install.sh
	@echo "安装完成！运行: source ~/.bashrc"

# 卸载
uninstall:
	@echo "卸载 AI CLI..."
	./uninstall.sh
	@echo "卸载完成！"

# 运行测试
test:
	@echo "运行测试..."
	python3 -m pytest tests/ -v --cov=tools --cov-report=term-missing

# 清理缓存文件
clean:
	@echo "清理缓存文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	@echo "清理完成！"

# 代码检查
lint:
	@echo "代码检查..."
	python3 -m flake8 tools/ ai.py --max-line-length=100 --exclude=__pycache__
	python3 -m pylint tools/ ai.py --disable=C0114,C0115,C0116

# 格式化代码
format:
	@echo "格式化代码..."
	python3 -m black tools/ ai.py --line-length=100
	python3 -m isort tools/ ai.py --profile black
	@echo "格式化完成！"

# 生成文档
docs:
	@echo "生成文档..."
	python3 -m pdoc --html --output-dir docs/ tools/
	@echo "文档已生成到 docs/ 目录"

# 更新程序
update:
	@echo "更新程序..."
	git pull origin main
	@echo "更新完成！"

# 显示版本信息
version:
	@echo "AI CLI v$(shell cat version.txt)"

# 快速测试
quick-test:
	@echo "快速测试..."
	python3 -c "from tools.core import LeaderAI, WorkerAI, TaskManager, AIInitializer; print('✓ 核心模块导入成功')"
	python3 -c "from tools.chat import ChatEngine; print('✓ Chat 模块导入成功')"
	python3 ai.py help | head -10
