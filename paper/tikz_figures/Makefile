ENGINE ?= xelatex
FIGS := fig_system_arch fig_gan_jscc fig_system_run fig_tvm_pipeline fig_tvm_opt_flow \
        fig_baseline_current fig_mnn_arch fig_geometric_computing fig_mnn_dynamic \
        fig_mnn_resize fig_perf_bar

.PHONY: all clean

all: $(addsuffix .pdf,$(FIGS))

%.pdf: %.tex _preamble.tex
	$(ENGINE) -interaction=nonstopmode -halt-on-error $<

clean:
	rm -f $(addsuffix .pdf,$(FIGS)) $(addsuffix .aux,$(FIGS)) $(addsuffix .log,$(FIGS))
