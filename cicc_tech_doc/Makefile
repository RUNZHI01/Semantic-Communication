TEX=main
ENGINE?=xelatex

.PHONY: build clean

build:
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -xelatex -interaction=nonstopmode -halt-on-error $(TEX).tex; \
	else \
		$(ENGINE) -interaction=nonstopmode -halt-on-error $(TEX).tex && \
		biber $(TEX) && \
		$(ENGINE) -interaction=nonstopmode -halt-on-error $(TEX).tex && \
		$(ENGINE) -interaction=nonstopmode -halt-on-error $(TEX).tex; \
	fi

clean:
	@if command -v latexmk >/dev/null 2>&1; then \
		latexmk -C; \
	else \
		rm -f $(TEX).aux $(TEX).log $(TEX).out $(TEX).toc $(TEX).pdf $(TEX).xdv \
		      $(TEX).bbl $(TEX).blg $(TEX).bcf $(TEX).run.xml $(TEX).fdb_latexmk $(TEX).fls; \
	fi
