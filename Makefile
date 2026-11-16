# SPDX-License-Identifier: GPL-3.0-or-later
PREFIX ?= /usr
DESTDIR ?=
CC ?= cc
CFLAGS ?= -O2 -g
WARN = -std=c11 -Wall -Wextra -Werror
CORE = src/transport.c src/protocol.c src/sensors.c src/hardware.c src/control.c src/maximum.c
.PHONY: all check install clean dist
all: build/ec-worker
build/ec-worker: $(CORE) src/worker.c src/fan.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) $(CORE) src/worker.c $(LDFLAGS) -o $@
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
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
install: all
	install -Dm755 build/ec-worker $(DESTDIR)$(PREFIX)/lib/asus-zenbook-fan-driver/ec-worker
	install -Dm755 src/service.py $(DESTDIR)$(PREFIX)/lib/asus-zenbook-fan-driver/service.py
	install -Dm755 src/client.py $(DESTDIR)$(PREFIX)/bin/asus-zenbook-fan-driver
	install -Dm644 systemd/asus-zenbook-fan-driver.service $(DESTDIR)$(PREFIX)/lib/systemd/system/asus-zenbook-fan-driver.service
	install -Dm755 systemd/asus-zenbook-fan-driver-sleep $(DESTDIR)$(PREFIX)/lib/systemd/system-sleep/asus-zenbook-fan-driver
	install -Dm644 LICENSE $(DESTDIR)$(PREFIX)/share/licenses/asus-zenbook-fan-driver/LICENSE
	install -Dm644 docs/LICENSE.MIT-reference $(DESTDIR)$(PREFIX)/share/licenses/asus-zenbook-fan-driver/LICENSE.MIT-reference
	install -Dm644 README.md $(DESTDIR)$(PREFIX)/share/doc/asus-zenbook-fan-driver/README.md
	install -Dm644 docs/PROVENANCE.md $(DESTDIR)$(PREFIX)/share/doc/asus-zenbook-fan-driver/PROVENANCE.md
clean:
	rm -rf build
dist:
	mkdir -p dist
	git archive --format=tar --prefix=asus-zenbook-fan-driver-0.1.0/ v0.1.0 | gzip -n > dist/asus-zenbook-fan-driver-0.1.0.tar.gz
