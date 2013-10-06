JSIN=$(wildcard res/*.js) $(wildcard js/*.js) generate_js_hand/packets.js generate_js_hand/packhand_gen.js

all: compiled/webclient.js compiled/webclient.css

compiled/webclient.js: $(JSIN)
	cat $(JSIN) > compiled/webclient.js
compiled/webclient.css: $(wildcard css/*.js)
	cat $(wildcard css/*.css) > compiled/webclient.css

generate_js_hand/packets.js:
	cd generate_js_hand; ./generate_packets.py

generate_js_hand/packhand_gen.js:
	cd generate_js_hand; ./generate_js_hand.py
