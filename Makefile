ALL_CARDS = $(patsubst src_img/%.png, cards/%.png, $(wildcard src_img/*.png))

cards/%.png: src_img/%.png
	./card_scripts/make_$*.sh $< $@

all_cards: $(ALL_CARDS)

subs: all_cards karaoke.txt subtitle_render.py
	./subtitle_render.py $(FROM) $(TO) $(RENDER_FLAGS) --rm -k orig_subs/karaoke.txt -O subs/ small/frame_0000*.png

play: subs
	./play.sh $<

clean:
	rm -f cards/*.png

.PHONY: subs play clean
