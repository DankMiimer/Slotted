# Cartridge drawings

Our MIT geometric shell and moulding SVGs represent the two physical Game Pak designs.
Both use a 360×245 canvas so the carousel and native top-loader motion share their geometry.
Moulding gradients, rounded label recesses and fine plastic grain replace flat fills and the
hard diagonal label frame. The generated asset fingerprint invalidates just the changed
shell's baked carts.

- Europe/Japan: flat top, wide rounded label well, narrow side grips, front panel seams,
  finger recess and lower security screws.
- North America: raised centre panel, narrower label well, six bevelled horizontal grip panels,
  finger recess and lower security screws.

Visual references: SNES Central's photographs of a [European Donkey Kong Country cart](https://snescentral.com/cart.php?id=0105&num=5)
and a [USA Super Mario World cart](https://snescentral.com/cart_test.php?id=0000&num=3).
The PAL top is gently curved across the full width. Both shells use recessed game-bit screw
heads. No photographs, game labels or manufacturer logos are included in these SVGs.

The NES shell is our own MIT drawing of the rectangular 304×337 Game Pak, with its left
ribbed grip, tall right label, recessed arrow, top notches and stepped connector edge.
The continuous bezel represents the front-loader tray. Grey and Zelda gold variants share
the same moulding. Proportions were checked against Evan-Amos's public-domain
[NES cartridge photograph](https://commons.wikimedia.org/wiki/File:NES-Cartridge.jpg);
no photograph pixels are included in the assets.

N64 is our own 360×241 drawing with its broad arched top, full-height side-panel seams,
lower finger recesses and portrait label well. The dark deck has one continuous housing.
The public-domain [Evan-Amos N64 cartridge photograph](https://commons.wikimedia.org/wiki/File:N64-Game-Cartridge.jpg)
was used for shell construction; regional LaunchBox Cart - Front records were used to calibrate
the label well and North American front colours. Examples include
[yellow Donkey Kong 64](https://images.launchbox-app.com/44fa4e81-13bb-44aa-8ef9-2e7adf6587fa.png)
and [gold Pokémon Stadium 2](https://images.launchbox-app.com/690a1e6c-97c1-4826-b691-75c96d4f7918.png). No photographs, printed labels
or manufacturer logos are included in these SVGs. The baker downloads label art on the device.

Genesis/Mega Drive uses our own MIT drawings on a shared 360×270 canvas. The Western body has
broad smooth shoulders and a curved bottom edge. Japan's shell has projecting ribbed grips
and a raised central panel. The taller Electronic Arts body preserves its yellow moulded
grip as a separate colour layer; Blades of Vengeance selects this verified variant.
The three silhouettes keep their physical aspect ratios. A common landscape video window
fits inside all three printed labels, and the socket has one continuous chamfered housing.

Proportions and label crops were checked against LaunchBox Cart - Front photographs of
[Western Sonic 2](https://images.launchbox-app.com/ace55579-164e-41d8-b3a4-74f4c540d99e.png),
[Japanese Sonic 2](https://images.launchbox-app.com/648bb2af-41e4-46ee-82f1-17302642e580.png) and
[Blades of Vengeance](https://images.launchbox-app.com/4d025fd3-9bbe-4d20-9a52-c5162a078823.png).
The SVGs include no photographed pixels, printed game labels or manufacturer logos.

PSP's procedural source is `tools/themebuild/umd.py`: a white UMD case with a rounded crown,
straight flanks and shallow curved base, an opaque label window, and an original rear housing
with a bottom-hinged drive door. Its pose shares the PS1 camera. The rear loading direction was
checked against Sony's [PSP-3004 quick reference](https://www.playstation.com/content/dam/global_pdc/en-gb/corporate/support/manuals/psp-docs/psp-3004/PSP-3004-QR$en-gb.pdf).
Regional LaunchBox Disc scans are downloaded separately by the baker. No reference photograph
or printed game artwork is included in the generated theme assets.

DS uses our own MIT rounded game-card outline and moulding on a 312×341 canvas.
Its wide recessed label and common video window remain opaque. The opposite native face
is original plastic and connector artwork, with no downloaded pixels. Complete DS Lite
geometry is built by `tools/consolebuild/models.py`; its label-down rear loading direction
follows [Nintendo's instructions](https://en-americas-support.nintendo.com/app/answers/detail/a_id/3906/~/how-to-insert-and-play-a-nintendo-ds-game-card).
Regional printed labels are downloaded separately by the baker.

Pico-8 uses our MIT 160×205 pixel cartridge outline and fallback moulding, generated at
264×338. Its square label is at (16,24)–(144,152), following the
[official cartridge format](https://www.lexaloffle.com/dl/docs/pico-8_manual.html).
The baker preserves a local PNG cart's full RGB artwork and credits using nearest-neighbour
scaling, replaces display alpha with our opaque silhouette, and leaves the encoded ROM
unchanged. Text carts use bounded `__label__` reads. No game artwork is shipped here.
