import io
from flask import Flask, request
import pyarrow as pa
import geoarrow.pyarrow as ga
import pyarrow.parquet as parquet
import pyarrow.ipc as ipc
import pyarrow.feather as feather


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

    with io.BytesIO() as f:
        parquet.ParquetWriter(f, tab.schema, compression=compression, compression_level=compression_level)
        return bytes(f)

@app.route("/stream_ipc")
def stream_ipc():
    def generate():
        max_chunk_size_bytes = request.args.get("max_chunk_size_bytes", None)
        chunked_geometry = geometry
        if max_chunk_size_bytes:
            chunked_geometry = ga.rechunk(chunked_geometry, max_chunk_size_bytes)

        schema = pa.schema([pa.field("geometry", chunked_geometry.type)])

        with io.BytesIO() as f, ipc.new_stream(f, schema) as stream:
            yield f.getbuffer()

            for chunk in geometry.chunks:
                batch = pa.record_batch([chunk], names=["geometry"])
                f.truncate(0)
                stream.write_batch(batch)
                yield f.getbuffer()

    return app.response_class(generate(), mimetype='application/vnd.apache.arrow.stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
