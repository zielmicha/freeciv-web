all: compiled/webclient.js compiled/webclient.css

compiled/webclient.js: $(wildcard javascript/*.js)
	cat $(wildcard javascript/*.js) > compiled/webclient.js
compiled/webclient.css: $(wildcard css/*.js)
	cat $(wildcard css/*.css) > compiled/webclient.css
