# Makefile for enhanced TikZ figures
# 用于批量编译所有增强版学术架构图

# LaTeX 编译器（必须使用 XeLaTeX 以支持中文）
LATEX = xelatex

# 所有 .tex 源文件
SOURCES = $(wildcard fig_*_enhanced.tex)

# 对应的 PDF 输出文件
PDFS = $(SOURCES:.tex=.pdf)

# 默认目标：编译所有图表
.PHONY: all
all: $(PDFS)
	@echo "============================================"
	@echo "✅ 所有图表编译完成！"
	@echo "============================================"
	@echo "生成的 PDF 文件："
	@ls -lh $(PDFS)

# 编译规则：.tex → .pdf
%.pdf: %.tex
	@echo "📊 正在编译 $< ..."
	$(LATEX) -interaction=nonstopmode $<
	@echo "✅ $@ 编译完成"
	@echo ""

# 清理辅助文件
.PHONY: clean
clean:
	@echo "🧹 清理辅助文件..."
	rm -f *.aux *.log *.out *.toc *.synctex.gz *.fls *.fdb_latexmk
	@echo "✅ 清理完成"

# 深度清理（包括 PDF）
.PHONY: distclean
distclean: clean
	@echo "🧹 深度清理（包括 PDF）..."
	rm -f $(PDFS)
	@echo "✅ 深度清理完成"

# 重新编译所有图表
.PHONY: rebuild
rebuild: distclean all

# 单独编译特定图表
.PHONY: gan
gan:
	$(LATEX) fig_gan_jscc_enhanced.tex

.PHONY: system
system:
	$(LATEX) fig_system_arch_enhanced.tex

.PHONY: tvm
tvm:
	$(LATEX) fig_tvm_pipeline_enhanced.tex

.PHONY: mnn
mnn:
	$(LATEX) fig_mnn_arch_enhanced.tex

.PHONY: optflow
optflow:
	$(LATEX) fig_tvm_opt_flow_enhanced.tex

.PHONY: perf
perf:
	$(LATEX) fig_perf_comparison_enhanced.tex

.PHONY: geo
geo:
	$(LATEX) fig_geometric_computing_enhanced.tex

# 帮助信息
.PHONY: help
help:
	@echo "============================================"
	@echo "增强版 TikZ 学术架构图 - Makefile 使用说明"
	@echo "============================================"
	@echo ""
	@echo "可用命令："
	@echo "  make all        - 编译所有图表（默认）"
	@echo "  make clean      - 清理辅助文件（.aux, .log 等）"
	@echo "  make distclean  - 深度清理（包括 PDF）"
	@echo "  make rebuild    - 重新编译所有图表"
	@echo ""
	@echo "单独编译特定图表："
	@echo "  make gan        - GAN-based JSCC 结构图"
	@echo "  make system     - 系统架构图"
	@echo "  make tvm        - TVM 编译流水线"
	@echo "  make mnn        - MNN 架构图"
	@echo "  make optflow    - TVM 优化流程图"
	@echo "  make perf       - 性能对比柱状图"
	@echo "  make geo        - 几何计算机制图"
	@echo ""
	@echo "依赖要求："
	@echo "  - XeLaTeX（支持中文）"
	@echo "  - TikZ/PGF 宏包"
	@echo "  - 中文字体（SimHei 或 STHeiti）"
	@echo ""
