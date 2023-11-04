import io
from flask import Flask, request
import pyarrow as pa
import geoarrow.pyarrow as ga
import pyarrow.parquet as parquet
import pyarrow.ipc as ipc
import pyarrow.feather as feather
import time


app = Flask(__name__)

geometry = feather.read_table("ns-water-water_line.arrow")["wkb_geometry"]


@app.route("/")
def index():
    with open("test.html") as f:
        return f.read()


@app.route("/fetch_parquet")
def fetch_parquet():
    compression = request.args.get("compression", "NONE")
    compression_level = request.args.get("compression_level", None)
    if compression_level is not None:
        compression_level = int(compression_level)

    tab = pa.table([geometry], names=["geometry"])

    t0 = time.time()
    with io.BytesIO() as f:
        writer = parquet.ParquetWriter(
            f, tab.schema, compression=compression, compression_level=compression_level
        )
        writer.write_table(tab)

        t1 = time.time()
        print(f"Wrote {len(f.getbuffer())} bytes in {t1 - t0} secs")

        return app.response_class(
            f.getvalue(), mimetype="application/vnd.apache.parquet"
        )


@app.route("/stream_ipc")
def stream_ipc():
    def generate(max_chunk_size_bytes, options):
        t0 = time.time()
        chunked_geometry = geometry
        if max_chunk_size_bytes:
            chunked_geometry = ga.rechunk(chunked_geometry, int(max_chunk_size_bytes))

        schema = pa.schema([pa.field("geometry", chunked_geometry.type)])

        with io.BytesIO() as f, ipc.new_stream(f, schema, options=options) as stream:
            yield f.getvalue()

            for chunk in chunked_geometry.chunks:
                batch = pa.record_batch([chunk], names=["geometry"])
                f.seek(0)
                f.truncate(0)
                stream.write_batch(batch)
                yield f.getvalue()

            t1 = time.time()
            print(f"{len(geometry)} features served in {t1 - t0} secs")

    max_chunk_size_bytes = request.args.get("max_chunk_size_bytes", None)
    compression = request.args.get("compression", None)
    compression_level = request.args.get("compression_level", None)

    if compression is not None and compression_level is not None:
        compression = pa.Codec(compression, int(compression_level))

    options = ipc.IpcWriteOptions(compression=compression)

    return app.response_class(
        generate(max_chunk_size_bytes, options),
        mimetype="application/vnd.apache.arrow.stream",
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
