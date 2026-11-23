<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Licensing

Copyright (C) 2026 1sSay.

asus-zenbook-fan-driver is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version. The complete license is in [LICENSE](LICENSE).

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

## Scope and notices

Authored application code, tests, build rules, service/desktop integration and
documentation use `GPL-3.0-or-later`, as identified by their SPDX headers.
Contributions to these files must be compatible with that license.

The independent AUR recipes and preparation tools under `packaging/` use
`0BSD`; their permission and warranty notice is in
[packaging/LICENSE](packaging/LICENSE). This exception does not relicense the
application. Generated `.SRCINFO` describes the packaged application's licenses.

Protocol references and possible adaptations are credited to Keyitdev
(GPLv3 or later) and Karmel0x (MIT). Preserve the attributions in the source and
[docs/PROVENANCE.md](docs/PROVENANCE.md), and the complete MIT notice in
[docs/LICENSE.MIT-reference](docs/LICENSE.MIT-reference). These references do not
grant rights to ASUS binaries, Windows drivers or firmware; none are shipped.

## Why GPLv3 or later

GPLv3 provides strong copyleft when covered software is distributed: recipients
must receive the applicable license and access to corresponding source under
its terms, including distributed modifications. It allows commercial use and
private modifications. It also fits the GPLv3-or-later protocol reference;
switching the combined application to a permissive license would require a
separate rights review. The `or-later` choice lets recipients use a later GNU
GPL version.

The installed package includes the GPL text, this explanation, provenance and
the retained MIT notice under `/usr/share/licenses/asus-zenbook-fan-driver/`
and `/usr/share/doc/asus-zenbook-fan-driver/`. AUR packaging also installs its
0BSD notice. When distributing binaries, keep the corresponding source for
that exact version available as required by GPLv3; a recipe alone is not the
corresponding source.
