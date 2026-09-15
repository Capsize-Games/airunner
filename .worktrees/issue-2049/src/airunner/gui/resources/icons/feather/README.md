Legacy Qt resource directory for the app icon set.

The directory name remains `feather` because the existing Qt `.ui` files,
generated UI Python modules, and compiled resource module all reference that
resource path today.

Current state:
- Standard icon SVGs in `light/` and `dark/` are now sourced from Lucide when
  Lucide provides a matching icon or alias.
- `dark/` contains white-stroked copies of the corresponding `light/` assets.
- Project-specific icons remain local: `dice-game-icon.svg`,
  `eraser-icon.svg`, `object-selected-icon.svg`, and `pencil-icon.svg`.
- Brand and social icons not shipped by Lucide core remain on their previous
  vendored artwork until they are replaced with a different approved source.

Upstream licensing for the Lucide-sourced assets is recorded in
`LUCIDE_LICENSE.txt`.