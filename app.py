import io
from flask import Flask, request
import pyarrow as pa
import geoarrow.pyarrow as ga
import pyarrow.parquet as parquet
import pyarrow.ipc as ipc
import pyarrow.feather as feather


app = Flask(__name__)

tab = feather.read_table("ns-water-water_junc.arrow", columns=["geometry"])


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

    with io.BytesIO() as f:
        parquet.ParquetWriter(f, tab.schema, compression=compression, compression_level=compression_level)
        return bytes(f)

@app.route("/stream_ipc")
def stream_ipc():
    def generate():
        for row in iter_all_rows():
            yield f"{','.join(row)}\n"
    return app.response_class(generate(), mimetype='application/vnd.apache.arrow.stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
