## Embedded Sass Host

This package is an alternative to the [`sass`] package. It supports the same JS
API as `sass` and is maintained by the same team, but where the `sass` package
is pure JavaScript, `sass-embedded` is instead a JavaScript wrapper around a
native Dart executable. This means `sass-embedded` will generally be much faster
especially for large Sass compilations, but it can only be installed on the
platforms that Dart supports: Windows, Mac OS, and Linux.

[`sass`]: https://www.npmjs.com/package/sass

Despite being different packages, both `sass` and `sass-embedded` are considered
"Dart Sass" since they have the same underlying implementation. Since the first
stable release of the `sass-embedded` package, both packages are released at the
same time and share the same version number.

## Usage

This package provides the same JavaScript API as the `sass` package, and can be
used as a drop-in replacement:

```js
const sass = require('sass-embedded');

const result = sass.compile(scssFilename);

// OR

const result = await sass.compileAsync(scssFilename);
```

Unlike the `sass` package, the asynchronous API in `sass-embedded` will
generally be faster than the synchronous API since the Sass compilation logic is
happening in a different process.

See [the Sass website] for full API documentation.

[the Sass website]: https://sass-lang.com/documentation/js-api

### Legacy API

The `sass-embedded` package also supports the older JavaScript API that's fully
compatible with [Node Sass] (with a few exceptions listed below), with support
for both the [`render()`] and [`renderSync()`] functions. This API is considered
deprecated and will be removed in Dart Sass 2.0.0, so it should be avoided in
new projects.

[Node Sass]: https://github.com/sass/node-sass
[`render()`]: https://sass-lang.com/documentation/js-api/modules#render
[`renderSync()`]: https://sass-lang.com/documentation/js-api/modules#renderSync

Sass's support for the legacy JavaScript API has the following limitations:

* Only the `"expanded"` and `"compressed"` values of [`outputStyle`] are
  supported.

* The `sass-embedded` package doesn't support the [`precision`] option. Dart
  Sass defaults to a sufficiently high precision for all existing browsers, and
  making this customizable would make the code substantially less efficient.

* The `sass-embedded` package doesn't support the [`sourceComments`] option.
  Source maps are the recommended way of locating the origin of generated
  selectors.

* The `sass-embedded` package doesn't support the [`indentWidth`],
  [`indentType`], or [`linefeed`] options. It implements the legacy API as a
  wrapper around the new API, and the new API has dropped support for these
  options.

[`outputStyle`]: https://sass-lang.com/documentation/js-api/interfaces/LegacySharedOptions#outputStyle
[`precision`]: https://github.com/sass/node-sass#precision
[`indentWidth`]: https://sass-lang.com/documentation/js-api/interfaces/LegacySharedOptions#indentWidth
[`indentType`]: https://sass-lang.com/documentation/js-api/interfaces/LegacySharedOptions#indentType
[`linefeed`]: https://sass-lang.com/documentation/js-api/interfaces/LegacySharedOptions#linefeed

## How Does It Work?

The `sass-embedded` runs the Dart Sass [embedded compiler] as a separate
executable and uses the [Embedded Sass Protocol] to communicate with it over its
stdin and stdout streams. This protocol is designed to make it possible not only
to start a Sass compilation, but to control aspects of it that are exposed by an
API. This includes defining custom importers, functions, and loggers, all of
which are invoked by messages from the embedded compiler back to the host.

[embedded compiler]: https://github.com/sass/dart-sass#embedded-dart-sass
[Embedded Sass Protocol]: https://github.com/sass/sass/tree/main/spec/embedded-protocol.md

Although this sort of two-way communication with an embedded process is
inherently asynchronous in Node.js, this package supports the synchronous
`compile()` API using a custom [synchronous message-passing library] that's
implemented with the [`Atomics.wait()`] primitive.

[synchronous message-passing library]: https://github.com/sass/sync-message-port
[`Atomics.wait()`]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Atomics/wait

---

Disclaimer: this is not an official Google product.
