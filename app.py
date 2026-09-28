from flask import Flask, Response, jsonify, redirect, render_template, request

from core import service, store

app = Flask(__name__)
store.init()


@app.get("/")
def index():
    return render_template("index.html", incidents=store.list_incidents(request.args.get("status")), summary=None)


@app.post("/upload")
def upload():
    f = request.files.get("logfile")
    if not f:
        return redirect("/")
    summary = service.process(f.read().decode("utf-8", "ignore").splitlines())
    return render_template("index.html", incidents=store.list_incidents(), summary=summary)


@app.post("/incident/<int:i>/status")
def status(i):
    store.set_status(i, request.form.get("status"))
    return redirect("/")


@app.get("/report/<int:i>")
def report(i):
    inc = store.get(i)
    if not inc:
        return "Not found", 404
    return Response(service.report(inc), mimetype="text/markdown",
                    headers={"Content-Disposition": f"attachment; filename=incident_{i}_rca.md"})


@app.get("/api/incidents")
def api():
    return jsonify(store.list_incidents(request.args.get("status")))


if __name__ == "__main__":
    app.run(debug=True)
