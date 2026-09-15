# `sync-message-port`

This package exposes a utility class that encapsulates the ability to send and
receive messages with arbitrary structure across Node.js worker boundaries. It
can be used as the building block for synchronous versions of APIs that are
traditionally only available asynchronously in the Node.js ecosystem by running
the asynchronous APIs in a worker and accessing their results synchronously from
the main thread.

See [the `sync-child-process` package] for an example of `sync-message-port` in
action.

[the `sync-child-process` package]: https://github.com/sass/sync-child-process

[**API Docs**]

[**API Docs**]: https://sass.github.io/sync-message-port/classes/SyncMessagePort.html

## Usage

1. Use [`SyncMessagePort.createChannel()`] to create a message channel that's
   set up to be compatible with `SyncMessagePort`s. A normal `MessageChannel`
   won't work!

2. You can send this `MessageChannel`'s ports across worker boundaries just like
   any other `MessagePort`. Send one to the worker you want to communicate with
   synchronously.

3. Once you're ready to start sending and receiving messages, wrap *both* ports
   in [`new SyncMessagePort()`], even if one is only ever going to be sending
   messages and not receiving them.

4. Use [`SyncMessagePort.postMessage()`] to send messages and
   `SyncMessagePort.receiveMessage()` to receive them synchronously.

[`SyncMessagePort.createChannel()`]: https://sass.github.io/sync-message-port/classes/SyncMessagePort.html#createChannel
[`new SyncMessagePort()`]: https://sass.github.io/sync-message-port/classes/SyncMessagePort.html#constructor
[`SyncMessagePort.postMessage()`]: https://sass.github.io/sync-message-port/classes/SyncMessagePort.html#postMessage
[`SyncMessagePort.receiveMessage()`]: https://sass.github.io/sync-message-port/classes/SyncMessagePort.html#receiveMessage

```js
import {Worker} from 'node:worker_threads';
import {SyncMessagePort} from 'sync-message-port';
// or
// const {SyncMessagePort} = require('sync-message-port');

// Channels must be created using this function. A MessageChannel created by
// hand won't work.
const channel = SyncMessagePort.createChannel();
const localPort = new SyncMessagePort(channel.port1);

const worker = new Worker(`
  import {workerData} from 'node:worker_threads';
  import {SyncMessagePort} from 'sync-message-port';

  const remotePort = new SyncMessagePort(workerData.port);

  setTimeout(() => {
    remotePort.postMessage("hello from worker!");
  }, 2000);
`, {
  workerData: {port: channel.port2},
  transferList: [channel.port2],
  eval: true,
});

// Note that because workers report errors asynchronously, this won't report an
// error if the worker fails to load because the main thread will be
// synchronously waiting for its first message.
worker.on('error', console.error);

console.log(localPort.receiveMessage());
```

## Why synchrony?

Although JavaScript in general and Node.js in particular are typically designed
to embrace asynchrony, there are a number of reasons why a synchronous API may
be preferable or even necessary.

### No a/synchronous polymorphism

Although `async`/`await` and the `Promise` API has substantially improved the
usability of writing asynchronous code in JavaScript, it doesn't address one
core issue: there's no way to write code that's *polymorphic* over asynchrony.
Put in simpler terms, there's no language-level way to write a complex function
that takes a callback and to run that functions synchronously if the callback is
synchronous and asynchronously otherwise. The only option is to write the
function twice.

This poses a real, practical problem when interacting with libraries. Suppose
you have a library that takes a callback option—for example, an HTML
sanitization library that takes a callback to determine how to handle a given
`<a href="...">`. The library doesn't need to do any IO itself, so it's written
synchronously. But what if your callback wants to make an HTTP request to
determine how to handle a tag? You're stuck unless you can make that request
synchronous. This library makes that possible.

### Performance considerations

Asynchrony is generally more performant in situations where there's a large
amount of concurrent IO happening. But when performance is CPU-bound, it's often
substantially worse due to the overhead of bouncing back and forth between the
event loop and user code.

As a real-world example, the Sass compiler API supports both synchronous and
asynchronous code paths to work around the polymorphism problem described above.
The logic of these paths is exactly the same—the only difference is that the
asynchronous path's functions all return `Promise`s instead of synchronous
values. Compiling with the asynchronous path often takes 2-3x longer than with
the synchronous path. This means that being able to run plugins synchronously
can provide a substantial overall performance gain, even if the plugins
themselves lose the benefit of concurrency.

## How does it work?

This uses [`Atomics`] and [`SharedArrayBuffer`] under the covers to signal
across threads when messages are available, and
[`worker_threads.receiveMessageOnPort()`] to actually retrieve messages.

[`Atomics`]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Atomics
[`SharedArrayBuffer`]: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/SharedArrayBuffer
[`worker_threads.receiveMessageOnPort()`]: https://nodejs.org/api/worker_threads.html#workerreceivemessageonportport

### Can I use this in a browser?

Unfortunately, no. Browsers don't support any equivalent of
`worker_threads.receiveMessageOnPort()`, even within worker threads. You could
make a similar package that can transmit only binary data (or data that can be
encoded as binary) using only `SharedArrayBuffer`, but that's outside the scope
of this package.

Disclaimer: this is not an official Google product.
