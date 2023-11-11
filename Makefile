ALL_CARDS = $(patsubst src_img/%.png, cards/%.png, $(wildcard src_img/*.png))
MAGI_ANSI = $(patsubst magi_ui/magi_ui_markup_%.txt, magi_ui/magi_ui_ansi_%.txt, $(wildcard magi_ui/magi_ui_markup_*.txt))
MAGI_BARE = $(patsubst magi_ui/magi_ui_markup_%.txt, magi_ui/magi_ui_bare_%.txt, $(wildcard magi_ui/magi_ui_markup_*.txt))

cards/%.png: src_img/%.png card_scripts/make_%.sh
	./card_scripts/make_$*.sh $< $@

magi_ui/magi_ui_ansi_%.txt: magi_ui/magi_ui_markup_%.txt add_ansi_colors.py
	python add_ansi_colors.py $< $@

magi_ui/magi_ui_bare_%.txt: magi_ui/magi_ui_markup_%.txt add_ansi_colors.py
	python add_ansi_colors.py --mode=stripmarkup $< $@

all_cards: $(ALL_CARDS)

all_magi: $(MAGI_ANSI) $(MAGI_BARE)

subs: all_cards orig_subs/karaoke.txt subtitle_render.py
	./subtitle_render.py $(FROM) $(TO) $(RENDER_FLAGS) --rm -k orig_subs/karaoke.txt -O subs/ small/frame_0000*.png

play: subs
	./play.sh $<

clean:
	rm -f cards/*.png

.PHONY: subs play clean
