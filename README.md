
# Streaming from Python to JS Experiments

Some experiments on tradeoffs involving streaming geoarrow from Python to JavaScript.
The Python half is a Flask app that will serve the test.html page at
`http://localhost:5000`. I highly reccomend opening the Mozilla developer tools
(in particular, the "network" tab) while running the experiments. This will show
latency, transfer times, and transfer sizes as seen by the browser.

## TL;DR

You should probably use an uncompressed IPC stream to send geometry from Python
to JS if you are serving from localhost: this is a case where the time it takes
to perform compression will dominate the time of the request. If you are serving
over WiFi speeds and slower, transport time will dominate. In this case, the
payoff of gzip compression is worth it as it results in the smallest transport
sizes. If you have the ability to stream your result (i.e., perform transport
and compression in parallel), gzip compression time
is negligible. If you don't, using ZSTD buffer compression may be worth it as
the compression time is ~2x faster.

## Fetch vs. Stream

Maybe not the best words for this, but in Flask you can return a single `bytes` or
return a generator of `bytes` to "stream" the response. Streaming obviously
is better for memory on the server but returning `bytes` probably avoids some
Python overhead and I wanted to make sure that overhead wasn't dominating the
results. As long as the chunk size was big enough (I used 1 MB), the overhead
of returning a generator still resulted in a faster end-to-end request.

## Compression

I tried three compression options: uncompressed, ZSTD level 7 (buffer-level compression)
and gzip (message-level compression). The example file I was using (ns-water_water-line
from https://geoarrow.org/data ) didn't compress all that well in any compression scheme:
uncompressed IPC resulted in 380 MB of transfer; ZSTD level 7 resulted in 322 MB transfer;
gzip compression resulted in 277 MB transfer. Streaming IPC with ZSTD compression was
about 6 times slower than streaming uncompressed; streaming IPC with gzip compression was
about 12 times slower than streaming uncompressed.

The advantage of gzip compression is that the decompression is handled transparently
by the browser via the `Content-Encoding: gzip` header and thus the stream can be used
by an IPC reader that doesn't support buffer compression.

Tradeoffs for Parquet compression were identical to IPC.

## Parquet vs. IPC

The timings and file sizes for Parquet and IPC were almost identical (IPC being
slightly faster and slightly smaller).
IPC has the advantage that the entire response is a valid and well-known entity:
the response of the Parquet version is more like a lot of Parquet files squished
together which you need custom machinery to read.
