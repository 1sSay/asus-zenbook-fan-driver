# SPDX-License-Identifier: GPL-3.0-or-later
PREFIX ?= /usr
DESTDIR ?=
CC ?= cc
VERSION ?= 0.1.0
DIST_REF ?= v$(VERSION)
CFLAGS ?= -O2 -g
WARN = -std=c11 -Wall -Wextra -Werror
CORE = src/transport.c src/protocol.c src/sensors.c src/hardware.c src/control.c src/maximum.c
.PHONY: all check install clean dist
all: build/ec-worker build/control-helper
build/ec-worker: $(CORE) src/worker.c src/fan.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) $(CORE) src/worker.c $(LDFLAGS) -o $@
build/control-helper: src/control-helper.c
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) $< $(LDFLAGS) -o $@
check: all
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) -D_POSIX_C_SOURCE=200809L -Isrc -include tests/fake_io.h -c src/transport.c -o build/fake-transport.o
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) -D_POSIX_C_SOURCE=200809L -Isrc -include tests/fake_io.h -c src/protocol.c -o build/fake-protocol.o
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) -Isrc tests/protocol.c build/fake-transport.o build/fake-protocol.o src/sensors.c $(LDFLAGS) -o build/test-protocol
	./build/test-protocol
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) -D_POSIX_C_SOURCE=200809L -Isrc -include tests/fake_io.h -c src/control.c -o build/fake-control.o
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) -Isrc tests/control.c build/fake-transport.o build/fake-protocol.o build/fake-control.o src/sensors.c src/maximum.c $(LDFLAGS) -o build/test-control
	./build/test-control
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) -D_DEFAULT_SOURCE -Isrc tests/lifecycle.c build/fake-transport.o build/fake-protocol.o build/fake-control.o src/sensors.c src/maximum.c $(LDFLAGS) -o build/test-lifecycle
	./build/test-lifecycle
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) -Isrc tests/worker.c $(LDFLAGS) -o build/test-worker
	./build/test-worker
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) -Isrc tests/control-helper.c $(LDFLAGS) -o build/test-control-helper
	./build/test-control-helper
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
install: all
	install -Dm755 build/ec-worker $(DESTDIR)$(PREFIX)/lib/asus-zenbook-fan-driver/ec-worker
	install -Dm755 build/control-helper $(DESTDIR)$(PREFIX)/lib/asus-zenbook-fan-driver/control-helper
	install -Dm644 src/client.py $(DESTDIR)$(PREFIX)/lib/asus-zenbook-fan-driver/client.py
	install -Dm644 src/gui.py $(DESTDIR)$(PREFIX)/lib/asus-zenbook-fan-driver/gui.py
	install -Dm644 polkit/org.asuszenbook.fan.control.policy $(DESTDIR)$(PREFIX)/share/polkit-1/actions/org.asuszenbook.fan.control.policy
	install -Dm644 desktop/asus-zenbook-fan-driver.desktop $(DESTDIR)$(PREFIX)/share/applications/asus-zenbook-fan-driver.desktop
	install -Dm755 src/service.py $(DESTDIR)$(PREFIX)/lib/asus-zenbook-fan-driver/service.py
	install -Dm755 src/client.py $(DESTDIR)$(PREFIX)/bin/asus-zenbook-fan-driver
	install -Dm644 systemd/asus-zenbook-fan-driver.service $(DESTDIR)$(PREFIX)/lib/systemd/system/asus-zenbook-fan-driver.service
	install -Dm755 systemd/asus-zenbook-fan-driver-sleep $(DESTDIR)$(PREFIX)/lib/systemd/system-sleep/asus-zenbook-fan-driver
	install -Dm644 LICENSE $(DESTDIR)$(PREFIX)/share/licenses/asus-zenbook-fan-driver/LICENSE
	install -Dm644 docs/LICENSE.MIT-reference $(DESTDIR)$(PREFIX)/share/licenses/asus-zenbook-fan-driver/LICENSE.MIT-reference
	install -Dm644 README.md $(DESTDIR)$(PREFIX)/share/doc/asus-zenbook-fan-driver/README.md
	install -Dm644 docs/STATUS.md $(DESTDIR)$(PREFIX)/share/doc/asus-zenbook-fan-driver/STATUS.md
	install -Dm644 docs/DESKTOP.md $(DESTDIR)$(PREFIX)/share/doc/asus-zenbook-fan-driver/DESKTOP.md
	install -Dm644 docs/PROVENANCE.md $(DESTDIR)$(PREFIX)/share/doc/asus-zenbook-fan-driver/PROVENANCE.md
clean:
	rm -rf build
dist:
	mkdir -p dist
	git archive --format=tar --prefix=asus-zenbook-fan-driver-$(VERSION)/ --output=dist/source.tar $(DIST_REF)
	gzip -n -c dist/source.tar > dist/asus-zenbook-fan-driver-$(VERSION).tar.gz
	rm dist/source.tar
